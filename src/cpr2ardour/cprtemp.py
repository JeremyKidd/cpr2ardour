from pathlib import Path

path = Path("tests/data/Sapphic3.cpr")
data = path.read_bytes()

terms = [
    b".wav",
    b".WAV",
    b"Audio",
    b"audio",
    b"Pool",
    b"Media",
    b"Record",
]

for term in terms:
    index = data.find(term)

    if index == -1:
        print(term.decode("ascii"), "not found")
        continue

    start = max(0, index - 80)
    end = min(len(data), index + 160)

    print()
    print("Found", term.decode("ascii"), "at offset", index)
    print(data[start:end])
    print(data[start:end].hex(" "))
