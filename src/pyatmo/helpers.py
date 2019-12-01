import logging
import time
from calendar import timegm
from datetime import datetime

LOG = logging.getLogger(__name__)

_BASE_URL = "https://api.netatmo.com/"


def postRequest(auth, url, params={}, timeout=30):
    postParams = {"access_token": auth.accessToken}
    postParams.update(params)
    resp = auth.postRequest(url=url, params=postParams, timeout=timeout)
    if "errors" in resp or "body" not in resp or "home" not in resp["body"]:
        LOG.debug("Errors in response: %s", resp)
    return resp


def toTimeString(value):
    return datetime.utcfromtimestamp(int(value)).isoformat(sep="_")


def toEpoch(value):
    return timegm(time.strptime(value + "GMT", "%Y-%m-%d_%H:%M:%S%Z"))


def todayStamps():
    today = timegm(time.strptime(time.strftime("%Y-%m-%d") + "GMT", "%Y-%m-%d%Z"))
    return today, today + 3600 * 24
