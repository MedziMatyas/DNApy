"""Small shims for third-party libraries that moved or were removed since this code was written."""

try:
    from pubsub import pub  # the standalone package: pip install PyPubSub
except ImportError:
    from wx.lib.pubsub import pub  # deprecated copy bundled with wxPython 4
