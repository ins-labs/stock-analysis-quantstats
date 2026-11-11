import copy
import csv
from datetime import date,timedelta
import json
import math
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import analyze
from command_runner import parse_command

COMMAND='python analyze.py --input data/synthetic-returns.csv --metadata data/synthetic-returns.metadata.json --periods-per-year 252 --rf 0 --compounding geometric --output results'
META=json.loads((analyze.ROOT/'data/synthetic-returns.metadata.json').read_text())


def reference(values,periods):
    wealth=peak=1.0;drawdown=0.0
    for r in values:
        wealth*=1+r;peak=max(peak,wealth);drawdown=min(drawdown,wealth/peak-1)
    sigma=statistics.stdev(values)
    return {'total_compounded_return':wealth-1,'cagr_observation_annualized':wealth**(periods/len(values))-1,
        'annualized_volatility_sample':sigma*math.sqrt(periods),'sharpe_rf_zero':statistics.mean(values)/sigma*math.sqrt(periods)if sigma else None,'max_drawdown':drawdown}


class MetricsTests(unittest.TestCase):
    def assert_scalar(self,values,periods=252):
        series=pd.Series(values,index=pd.date_range('2022-01-01',periods=len(values)))
        actual,undefined=analyze.numeric_metrics(series,periods)
        expected=reference(values,periods)
        for k,v in expected.items():
            if v is None:self.assertIsNone(actual[k]);self.assertIn(k,undefined)
            else:self.assertAlmostEqual(actual[k],v,places=10,msg=k)

    def test_fixture_against_scalar(self):
        series,meta,sha,msha=analyze.load_input(analyze.ROOT/'data/synthetic-returns.csv',analyze.ROOT/'data/synthetic-returns.metadata.json')
        self.assertEqual(len(series),756);self.assertEqual(series.index[0].date().isoformat(),'2022-01-03');self.assertEqual(series.index[-1].date().isoformat(),'2024-11-25')
        self.assertEqual(meta['dataset_kind'],'synthetic');self.assertEqual(len(sha),64);self.assertEqual(len(msha),64)
        self.assert_scalar(series.tolist())

    def test_alternate_annualization(self):self.assert_scalar([-.02,.01,.03,-.01,.005]*110,365)
    def test_first_negative_counts_drawdown(self):self.assert_scalar([-.15]+[0.0]*503)
    def test_all_zero_undefined_sharpe(self):self.assert_scalar([0.0]*504)
    def test_all_positive_stays_returns(self):self.assert_scalar([.002,.004,.001]*168)
    def test_all_negative_stays_returns(self):self.assert_scalar([-.002,-.004,-.001]*168)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.rows=[[(date(2022,1,1)+timedelta(days=i)).isoformat(),'.001'if i%2 else '-.002']for i in range(504)]

    def load(self,rows=None,meta=None,header=None):
        c=self.root/'x.csv';m=self.root/'m.json'
        with c.open('w',newline='')as f:
            w=csv.writer(f);w.writerow(header or ['Date','Return']);w.writerows(self.rows if rows is None else rows)
        m.write_text(json.dumps(META if meta is None else meta));return analyze.load_input(c,m)

    def test_minimum_504(self):self.assertEqual(len(self.load()[0]),504)
    def test_short_rejected(self):
        with self.assertRaises(ValueError):self.load(self.rows[:-1])
    def test_bad_values(self):
        for bad in ['nan','NaN','inf','-inf','',' ','-1','1','1.5','-2','None','oops']:
            with self.subTest(bad=bad):
                rows=copy.deepcopy(self.rows);rows[100][1]=bad
                with self.assertRaises(ValueError):self.load(rows)
    def test_bad_dates(self):
        for bad in ['', '2022/01/01','2022-1-1','2022-02-30','2022-01-01T00:00:00']:
            with self.subTest(bad=bad):
                rows=copy.deepcopy(self.rows);rows[100][0]=bad
                with self.assertRaises(ValueError):self.load(rows)
    def test_duplicate(self):
        rows=copy.deepcopy(self.rows);rows[100][0]=rows[99][0]
        with self.assertRaises(ValueError):self.load(rows)
    def test_unsorted(self):
        rows=copy.deepcopy(self.rows);rows[100],rows[101]=rows[101],rows[100]
        with self.assertRaises(ValueError):self.load(rows)
    def test_blank_and_wrong_width(self):
        for row in [[],[''],['2022-04-11'],['2022-04-11','.1','extra']]:
            rows=copy.deepcopy(self.rows);rows[100]=row
            with self.assertRaises(ValueError):self.load(rows)
    def test_wrong_header(self):
        with self.assertRaises(ValueError):self.load(header=['Date','Close'])
    def test_metadata_missing(self):
        for k in ['dataset_kind','instrument','source','as_of','timezone','return_basis','frequency','publication_rights','return_type']:
            meta=copy.deepcopy(META);del meta[k]
            with self.subTest(k=k),self.assertRaises(ValueError):self.load(meta=meta)
    def test_asof_offset_required(self):
        meta=copy.deepcopy(META);meta['as_of']='2026-11-11T06:30:00'
        with self.assertRaises(ValueError):self.load(meta=meta)
    def test_asof_before_data(self):
        meta=copy.deepcopy(META);meta['as_of']='2021-12-31T23:00:00+02:00'
        with self.assertRaises(ValueError):self.load(meta=meta)
    def test_wrong_return_type(self):
        meta=copy.deepcopy(META);meta['return_type']='log_returns'
        with self.assertRaises(ValueError):self.load(meta=meta)
    def test_upstream_reinterpretation_refused(self):
        with patch.object(analyze.qs.utils,'_prepare_returns',side_effect=lambda x,**kw:x*2):
            with self.assertRaises(ValueError):self.load()
    def test_command_and_paths(self):
        self.assertIn('analyze.py',parse_command(COMMAND)[1])
        for cmd in ['', 'echo hello',COMMAND+'; echo nope',COMMAND.replace('data/synthetic-returns.csv','../secrets.csv'),COMMAND.replace('--rf 0','--rf .05'),COMMAND.replace('--compounding geometric','--compounding arithmetic'),COMMAND.replace('--periods-per-year 252','--periods-per-year 12')]:
            with self.subTest(cmd=cmd),self.assertRaises((ValueError,SystemExit)):parse_command(cmd)
    def test_data_network_guard(self):
        with patch.object(analyze.qs.utils,'download_returns'),patch.object(analyze.yf,'download'),patch.object(analyze.yf,'Ticker'),patch.object(analyze.socket.socket,'connect'),patch.object(analyze.socket,'create_connection'):
            analyze.disable_data_network()
            for f in [analyze.qs.utils.download_returns,analyze.yf.download,analyze.yf.Ticker,analyze.socket.create_connection]:
                with self.assertRaises(RuntimeError):f('MSFT')


class EoyAxisTests(unittest.TestCase):
    def test_actual_eoy_years_positions_and_unchanged_heights(self):
        import matplotlib.pyplot as plt
        from matplotlib.axes import Axes
        from plot_compat import eoy_year_ticks
        series, *_ = analyze.load_input(analyze.ROOT/'data/synthetic-returns.csv', analyze.ROOT/'data/synthetic-returns.metadata.json')
        original = Axes.set_xticklabels
        try:
            with eoy_year_ticks():
                fig = analyze.qs.plots.yearly_returns(series, benchmark=None, show=False, prepare_returns=False)
            self.assertIs(Axes.set_xticklabels, original)
            ax = fig.axes[0]
            self.assertEqual([x.get_text() for x in ax.get_xticklabels()], ['2022','2023','2024'])
            bars = ax.containers[0]
            for tick, bar in zip(ax.get_xticks(), bars, strict=True):
                self.assertAlmostEqual(tick, bar.get_x()+bar.get_width()/2)
            for year, bar in zip([2022,2023,2024], bars, strict=True):
                wealth=1.0
                for value in series[series.index.year==year]:wealth*=1+value
                self.assertAlmostEqual(bar.get_height(), wealth-1, places=12)
        finally:plt.close('all')

    def test_eoy_adapter_restores_after_error(self):
        from matplotlib.axes import Axes
        from plot_compat import eoy_year_ticks
        original=Axes.set_xticklabels
        with self.assertRaises(RuntimeError):
            with eoy_year_ticks():raise RuntimeError('simulated report failure')
        self.assertIs(Axes.set_xticklabels, original)


if __name__=='__main__':unittest.main()
