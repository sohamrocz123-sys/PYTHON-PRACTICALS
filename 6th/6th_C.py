filename = "example.txt"

with open(filename, "w") as f:
    f.write("First line\n")

with open(filename, "a") as f:
    f.write("appended line\n")