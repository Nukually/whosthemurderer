import json


def encode_message(message):
    return (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")


def decode_message(raw_line):
    if not raw_line:
        return None
    return json.loads(raw_line)


def send_message(writer, message):
    writer.write(encode_message(message))
    writer.flush()
