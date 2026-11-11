"""QuantStats0.0.86 EOY tick-position adapter for the pinned report recipe."""
from contextlib import contextmanager
from unittest.mock import patch

from matplotlib.axes import Axes
from matplotlib.container import BarContainer


@contextmanager
def eoy_year_ticks():
    """Bind existing EOY year labels to existing bar centers, changing no data.

    Upstream plot_returns_bars sets labels without fixing the locator. Limit
    interception to the one no-benchmark EOY plot, require one bar series and
    one label per bar, and restore the original method even on report failure.
    """
    original = Axes.set_xticklabels

    def bound_labels(ax, labels, *args, **kwargs):
        title = ax.figure._suptitle
        if title is not None and title.get_text() == 'EOY Returns':
            bars = [c for c in ax.containers if isinstance(c, BarContainer)]
            if len(bars) != 1 or len(bars[0]) != len(labels):
                raise ValueError('EOY axis shape changed; refusing unbound year labels')
            positions = [bar.get_x() + bar.get_width()/2 for bar in bars[0]]
            ax.set_xticks(positions)
        return original(ax, labels, *args, **kwargs)

    with patch.object(Axes, 'set_xticklabels', bound_labels):
        yield
