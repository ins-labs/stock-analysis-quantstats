"""Explicit fractional daily returns only. No ticker or benchmark input."""
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
from importlib.metadata import version
import io
import json
import math
import os
from pathlib import Path
import re
import socket
import sys
from zoneinfo import ZoneInfo

os.environ.setdefault('MPLBACKEND', 'Agg')
import matplotlib
matplotlib.use('Agg')
import pandas as pd
import quantstats as qs
import yfinance as yf
from plot_compat import eoy_year_ticks

ROOT = Path(__file__).resolve().parent


def refuse_network(*args, **kwargs):
    raise RuntimeError('Network data access is disabled in this returns-only command')


def disable_data_network():
    # Defense in depth for this fixed no-benchmark recipe, not an OS firewall.
    qs.utils.download_returns = refuse_network
    yf.download = refuse_network
    yf.Ticker = refuse_network
    socket.socket.connect = refuse_network
    socket.create_connection = refuse_network


def data_path(value, suffix):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT/'data') or path.suffix != suffix or not path.is_file():
        raise ValueError('Input must be an existing data/ file with suffix '+suffix)
    return path


def parser():
    p=argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument('--input', required=True)
    p.add_argument('--metadata', required=True)
    p.add_argument('--periods-per-year', type=int, choices=[252,365], required=True)
    p.add_argument('--rf', type=float, choices=[0.0], required=True)
    p.add_argument('--compounding', choices=['geometric'], required=True)
    p.add_argument('--output', choices=['results'], default='results')
    return p


def load_input(csv_path, meta_path):
    if csv_path.stat().st_size>10_000_000 or meta_path.stat().st_size>100_000:
        raise ValueError('CSV limit 10 MB; metadata limit 100 KB')
    raw, mraw=csv_path.read_bytes(),meta_path.read_bytes()
    meta=json.loads(mraw)
    required=['dataset_kind','instrument','source','as_of','timezone','return_basis','frequency','publication_rights','return_type']
    if not isinstance(meta,dict) or any(not isinstance(meta.get(k),str) or not meta[k].strip() for k in required):
        raise ValueError('Metadata requires non-empty strings: '+', '.join(required))
    if meta['dataset_kind'] not in ['synthetic','market'] or meta['frequency']!='daily_observations':
        raise ValueError('Declare synthetic/market dataset_kind and frequency daily_observations')
    if meta['return_type']!='simple_fractional':raise ValueError('return_type must explicitly be simple_fractional')
    zone=ZoneInfo(meta['timezone']);asof=datetime.fromisoformat(meta['as_of'])
    if asof.tzinfo is None or asof.utcoffset() is None:raise ValueError('as_of must include UTC offset')
    reader=csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True)
    if next(reader,None)!=['Date','Return']:raise ValueError('Header must be exactly Date,Return')
    dates,values=[],[]
    for row in reader:
        if len(row)!=2 or any(not x.strip() for x in row):raise ValueError('Blank or malformed record')
        label=row[0];day=date.fromisoformat(label)
        if day.isoformat()!=label or (dates and label<=dates[-1]):raise ValueError('Unique strictly chronological ISO dates required')
        if day>asof.astimezone(zone).date():raise ValueError('Input date after declared as_of')
        value=float(row[1])
        if not math.isfinite(value) or not -1<value<1:
            raise ValueError('Fractional simple returns must be finite and strictly between -1 and 1; not percentages, prices, log returns or bankrupt series')
        dates.append(label);values.append(value)
    if len(dates)<504:raise ValueError('At least 504 daily observations required for this full-report recipe')
    series=pd.Series(values,index=pd.DatetimeIndex(dates),dtype='float64',name='Strategy')
    # Never trust the upstream heuristic to reinterpret this explicit schema.
    prepared=qs.utils._prepare_returns(series.copy(),apply_rf=False)
    if not series.equals(prepared):raise ValueError('Upstream preparation changed explicit returns')
    return series,meta,hashlib.sha256(raw).hexdigest(),hashlib.sha256(mraw).hexdigest()


def numeric_metrics(returns, periods):
    raw={'total_compounded_return':qs.stats.comp(returns),
         'cagr_observation_annualized':qs.stats.cagr(returns,rf=0.0,compounded=True,periods=periods),
         'annualized_volatility_sample':qs.stats.volatility(returns,periods=periods,annualize=True,prepare_returns=False),
         'sharpe_rf_zero':qs.stats.sharpe(returns,rf=0.0,periods=periods,annualize=True,smart=False),
         'max_drawdown':qs.stats.max_drawdown(returns)}
    values={k:float(v) if math.isfinite(float(v)) else None for k,v in raw.items()}
    return values,{k:'undefined or non-finite under this input; not replaced with zero'for k,v in values.items()if v is None}


def run(args):
    disable_data_network()
    series,meta,input_hash,metadata_hash=load_input(data_path(args.input,'.csv'),data_path(args.metadata,'.json'))
    metrics,undefined=numeric_metrics(series,args.periods_per_year)
    wealth=(1+series).cumprod();peak=wealth.cummax().clip(lower=1.0)
    curve=pd.DataFrame({'Date':series.index.strftime('%Y-%m-%d'),'Return':series.to_numpy(),'Wealth':wealth.to_numpy(),'Drawdown':(wealth/peak-1).to_numpy()})
    if any(not math.isfinite(float(v)) or float(v)<=0 for v in wealth):
        raise ValueError('Cumulative wealth overflow/underflow; input cannot be reported reliably')
    output=ROOT/'results'
    if output.is_symlink():raise ValueError('results must not be a symlink')
    output.mkdir(exist_ok=True)
    curve.to_csv(output/'returns-and-equity.csv',index=False)
    with (output/'metrics.csv').open('w',newline='')as f:
        writer=csv.writer(f);writer.writerow(['Metric','Value','UndefinedReason'])
        writer.writerows((k,''if v is None else v,undefined.get(k,''))for k,v in metrics.items())
    # Use the pinned package template, remove its automatic external favicon.
    template=(Path(qs.__file__).parent/'report.html').read_text()
    template=re.sub(r'<link\b[^>]*rel="shortcut icon"[^>]*>', '',template)
    temp_template=output/'report-template.html';temp_template.write_text(template)
    try:
        with eoy_year_ticks():
            qs.reports.html(series.copy(),benchmark=None,rf=0.0,output=str(output/'tearsheet.html'),
                compounded=True,periods_per_year=args.periods_per_year,match_dates=False,
                title=meta['dataset_kind'].upper()+' RETURNS - NOT AN INVESTMENT RECOMMENDATION',
                strategy_title='Explicit returns CSV',figfmt='svg',template_path=str(temp_template),
                parameters={'Input SHA256':input_hash,'Input kind':meta['dataset_kind'],'Compounding':'geometric'})
    finally:temp_template.unlink(missing_ok=True)
    report=(output/'tearsheet.html').read_text()
    if '<svg'not in report or '{{'in report or re.search(r'<(?:script|img|link)\b[^>]*(?:src|href)=[\"\']https?://',report,re.I):
        raise ValueError('HTML incomplete or contains automatic external resource')
    summary={'status':'success','dataset':meta,'input':args.input,'input_sha256':input_hash,'metadata_sha256':metadata_hash,
        'observations':len(series),'start_date':series.index[0].date().isoformat(),'end_date':series.index[-1].date().isoformat(),
        'parameters':{'periods_per_year':args.periods_per_year,'rf_annual':0.0,'compounded':True,'benchmark':None,'match_dates':False},
        'metrics':metrics,'undefined_metrics':undefined,'versions':{n:version(n)for n in ['quantstats','numpy','pandas','matplotlib','scipy','seaborn','yfinance']},
        'python':sys.version,'generated_at':datetime.now(timezone.utc).isoformat(),
        'semantics':'Simple fractional supplied daily returns; product(1+r)-1; CAGR exponent periods_per_year/observations, NOT elapsed-calendar years; sample volatility ddof1*sqrt(periods); Sharpe mean/sample_std*sqrt(periods), annual rf fixed zero; geometric wealth baseline1 includes first loss in drawdown. Supplied gaps retained without imputation; calendar/trading completeness NOT verified. HTML ancillary metrics/plots follow pinned QuantStats conventions and are not all independently formula-qualified.',
        'limits':'No benchmark, symbol fetch, prices-to-returns conversion, fees/FX/adjustment inference or trading. Non-finite numeric metrics become JSON null/CSV blank with reason. Synthetic results are not market evidence.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    text=f"{meta['dataset_kind'].upper()} RETURNS: {meta['instrument']}\n{len(series)} observations: {summary['start_date']} through {summary['end_date']}\nSource: {meta['source']}\nAs of: {meta['as_of']}\nReturn basis: {meta['return_basis']}\nPeriods/year: {args.periods_per_year}; annual rf=0; compounded=True; benchmark=None\n"+'\n'.join(f'{k}: {v}'for k,v in metrics.items())+'\n'+summary['semantics']+'\n'+summary['limits']+'\n'
    (output/'summary.txt').write_text(text);print(text)
    return summary


def main(argv=None):
    args=parser().parse_args(argv)
    try:run(args)
    except (ValueError,OSError,KeyError,TypeError,OverflowError,RuntimeError,csv.Error)as exc:
        print('Analysis rejected: '+str(exc),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
