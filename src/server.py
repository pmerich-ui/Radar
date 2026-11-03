from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import hmac,json,os,threading
from urllib.parse import urlsplit
from .producer import produce
lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def send_json(self,code,obj):
        data=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code);self.send_header("Content-Type","application/json");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        self.send_json(200,{"ok":True,"mode":"prototype","publishing":"DISABLED"}) if urlsplit(self.path).path=="/health" else self.send_json(404,{"error":"not_found"})
    def do_POST(self):
        if urlsplit(self.path).path!="/render":return self.send_json(404,{"error":"not_found"})
        secret=os.environ.get("RENDER_JOB_TOKEN","")
        if len(secret)<32:return self.send_json(503,{"error":"secure_token_not_configured"})
        if not hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+secret):return self.send_json(401,{"error":"unauthorized"})
        if not lock.acquire(False):return self.send_json(429,{"error":"busy"})
        try:
            result=produce(Path("/tmp/dealradar-render"))
            result.pop("file",None)
            result["artifact"]="EPHEMERAL_LOCAL_ONLY"
            result["scheduled"]=False
            self.send_json(200,result)
        except Exception as e:self.send_json(500,{"error":"render_failed","type":type(e).__name__})
        finally:lock.release()
if __name__=="__main__":ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT","10000"))),Handler).serve_forever()
