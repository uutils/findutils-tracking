import sys

import matplotlib.pyplot as plt
import pandas as pd

file = sys.argv[1]
d = pd.read_json(file, orient="index")
df = pd.DataFrame(d)

df.columns.names = ["date"]

df.index = pd.to_datetime(df.index, utc=True)

print(df)

fig, ax = plt.subplots(figsize=(9.6, 7.2))

df.plot(y="total", color="blue", ax=ax)
df.plot(y="fail", color="gray", ax=ax, dashes=(2, 1))
df.plot(y="pass", color="green", ax=ax, dashes=(4, 1))
if "gnu" in file:
    df.plot(y="error", color="orange", ax=ax, dashes=(6, 2))
fig.autofmt_xdate()
plt.margins(0.01)
plt.ylim(ymin=0)
if "gnu" in file:
    plt.title("Rust/findutils running GNU testsuite")
    plt.savefig("gnu-results.svg", format="svg", dpi=199, bbox_inches="tight")
else:
    plt.title("Rust/findutils running BFS testsuite")
    plt.savefig("bfs-results.svg", format="svg", dpi=199, bbox_inches="tight")
