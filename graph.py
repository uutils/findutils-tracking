from datetime import datetime
from email.utils import parsedate

import sys
import time

import matplotlib.pyplot as plt
import pandas as pd

d = pd.read_json(sys.argv[1], orient="index")
df = pd.DataFrame(d)

df.columns.names = ["date"]

as_list = df.index.tolist()
for i in as_list:
    idx = as_list.index(i)
    as_list[idx] = str(i).split(" ")[0]

df.index = as_list

print(df)

ax = plt.gca()
df.plot(y="total", color="blue", ax=ax)
df.plot(y="fail", color="gray", ax=ax, dashes=(2, 1))
df.plot(y="pass", color="green", ax=ax, dashes=(4, 1))
if "gnu" in sys.argv[1]:
    df.plot(y="error", color="orange", ax=ax, dashes=(6, 2))
plt.title("Rust/findutils running other testsuites")
plt.xticks(rotation=45)
if "gnu" in sys.argv[1]:
    plt.savefig("gnu-results.png", dpi=199)
else:
    plt.savefig("bfs-results.png", dpi=199)
