with open("/results/temp/aioquic_key.log","r") as f:
    lines = f.read()
    lines = lines.replace("QUIC_", "")
    with open("/results/temp/aioquic2_key.log","w+") as f2:
        f2.write(lines)
