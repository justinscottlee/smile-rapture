import time

from flask import current_app


def utility_processor():
    def ts_formatted(ts):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))

    return dict(ts_formatted=ts_formatted)


def inject_current_app():
    return dict(current_app=current_app)
