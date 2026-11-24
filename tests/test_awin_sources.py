import gzip
import pytest
from cryptography.fernet import Fernet
from src import awin_sources as S

GOOD = gzip.compress(b"aw_product_id,product_name,aw_deep_link,merchant_id\n1,A,https://www.awin1.com/x,111\n")

@pytest.fixture
def cache(tmp_path):
    return S.Cache(tmp_path, Fernet(Fernet.generate_key()))

@pytest.mark.parametrize("url", ["http://productdata.awin.com/x","https://evil.example/x","https://user:pw@productdata.awin.com/x","https://productdata.awin.com:8443/x"])
def test_url(url):
    with pytest.raises(S.FeedError):
        S.check_url(url)

@pytest.mark.parametrize("data", [b"<html>",b"\x1f\x8bkaputt",gzip.compress(b"")])
def test_invalid(data):
    with pytest.raises(S.FeedError):
        S.inspect_gzip(data)

def test_cache(cache):
    cache.put("f1", GOOD)
    assert cache.get("f1")[0] == GOOD
    with pytest.raises(S.FeedError):
        cache.put("f1", b"bad")
    assert cache.get("f1")[0] == GOOD

def test_age(cache):
    cache.put("f1", GOOD)
    now = cache.now()
    cache.now = lambda: now + 8*86400
    with pytest.raises(S.FeedError):
        cache.get("f1")

def test_wrong_key(cache):
    cache.put("f1", GOOD)
    with pytest.raises(S.FeedError):
        S.Cache(cache.dir,Fernet(Fernet.generate_key())).get("f1")

def test_tamper(cache):
    cache.put("f1", GOOD)
    p = cache.path("f1")
    p.write_bytes(p.read_bytes()[:-8]+b"xxxxxxxx")
    with pytest.raises(S.FeedError):
        cache.get("f1")

def test_no_key(tmp_path):
    with pytest.raises(S.FeedError):
        S.Cache(tmp_path,None).put("f1",GOOD)
    assert not list(tmp_path.iterdir())

def test_path(cache):
    with pytest.raises(S.FeedError):
        cache.put("../escape",GOOD)

def test_bomb(monkeypatch):
    monkeypatch.setattr(S,"MAX_UNCOMPRESSED",100)
    with pytest.raises(S.FeedError):
        S.inspect_gzip(gzip.compress(b"x"*10000))

def test_filter(cache):
    cache.put("f1",GOOD)
    r=S.Result(feeds={"f1":{"tier":"live"}},joined={"111"})
    assert len(list(S.iter_products(cache,r)))==1
    r.joined=set()
    assert not list(S.iter_products(cache,r))

def test_callback(cache,tmp_path,monkeypatch):
    def fake(url,root,candidate_callback):
        p=root/"data/awin/incoming/scheduled.csv.gz"
        p.parent.mkdir(parents=True)
        p.write_bytes(GOOD)
        try:
            candidate_callback(root)
            return {"status":"COMPLETED"}
        finally:
            p.unlink()
    monkeypatch.setattr(S.aff,"download_and_audit",fake)
    S.fetch_live({"feed_id":"f1","url":"https://productdata.awin.com/x"},cache,tmp_path)
    assert cache.get("f1")[0]==GOOD

def test_missing_callback(cache,tmp_path,monkeypatch):
    monkeypatch.setattr(S.aff,"download_and_audit",lambda *a,**k:{"status":"COMPLETED"})
    with pytest.raises(S.FeedError):
        S.fetch_live({"feed_id":"f1","url":"https://productdata.awin.com/x"},cache,tmp_path)

def test_redact(monkeypatch):
    monkeypatch.setenv("AWIN_FEED_APIKEY","SECRET123")
    assert "SECRET123" not in S.redact("https://productdata.awin.com/SECRET123 SECRET123")

def test_bom():
    assert S.inspect_gzip(gzip.compress(b"\xef\xbb\xbf"+gzip.decompress(GOOD)))==1
