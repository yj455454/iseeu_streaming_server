from django.http import StreamingHttpResponse
from mysite.device_proxy import *

def stream(request, device_id):
    proxy = pool.get(device_id)
    if proxy:
        mjpeg = MjpegObserver(proxy).mjpeg() 
        return StreamingHttpResponse(mjpeg, content_type='multipart/x-mixed-replace;boundary=--myboundary')
    else:
        return f'{device_id} + proxy 없음'

