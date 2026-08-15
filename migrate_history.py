import json
import uuid
from datetime import datetime


source_file = "chat_history.json"


with open(
    source_file,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


if (
    isinstance(data, list)
    and data
    and isinstance(data[0], dict)
    and "messages" in data[0]
):

    print("Already migrated.")

else:

    chat = {
        "id": str(uuid.uuid4()),
        "title": "Old conversation",
        "created_at": datetime.now().isoformat(),
        "messages": data if isinstance(data, list) else []
    }

    with open(
        source_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            [chat],
            file,
            ensure_ascii=False,
            indent=2
        )

    print("MIGRATION OK")