import sys, hashlib, pathlib
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import storage

src = "/tmp/gm/a1.jpg"
data = pathlib.Path(src).read_bytes()
h = hashlib.sha1(data).hexdigest()[:12]
path = f"unoxdue/team/gianmarco-{h}.jpg"
res = storage.put_object(path, data, "image/jpeg")
print("UPLOAD_PATH=" + path)
print("RESULT=" + str(res))
print("PROD_URL=https://unoxdue.net/api/media/" + path)
