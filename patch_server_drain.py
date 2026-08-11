import re

with open("server/main.py", "r") as f:
    content = f.read()

drain_logic = """                audio_buffer.extend(chunk)

                # Drain pending binary chunks to catch up if CPU transcription is lagging
                while True:
                    try:
                        next_msg = await asyncio.wait_for(websocket.receive(), timeout=0.001)
                        if "bytes" in next_msg and next_msg["bytes"]:
                            nxt_chunk = next_msg["bytes"]
                            if len(nxt_chunk) % 2 != 0:
                                nxt_chunk = nxt_chunk[:-1]
                            audio_buffer.extend(nxt_chunk)
                        elif "text" in next_msg:
                            # If we hit a text/config message, put it back or ignore? 
                            # Since we can't un-receive, we just skip it if it's a ping, or process it if config.
                            try:
                                config = __import__("json").loads(next_msg["text"])
                                if config.get("type") == "ping":
                                    await websocket.send_json({"type": "pong"})
                            except:
                                pass
                            break
                    except __import__("asyncio").TimeoutError:
                        break

                # Maintain maximum buffer window (even byte aligned)"""

content = content.replace("                audio_buffer.extend(chunk)\n\n                # Maintain maximum buffer window (even byte aligned)", drain_logic)

with open("server/main.py", "w") as f:
    f.write(content)

