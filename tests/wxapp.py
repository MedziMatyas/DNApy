"""Helper for tests that need wxPython: there can only be one wx.App per process."""
try:
    import wx
except ImportError:  # the tests that need wx are skipped
    wx = None

_app = None


def get_app():
    global _app
    if wx is None:
        return None
    _app = wx.GetApp() or _app or wx.App(False)
    return _app
