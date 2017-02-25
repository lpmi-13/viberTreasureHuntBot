from pymongo import MongoClient

def checkUserStatus(user_id):
    db = MongoClient().users

    check = db.users.find({"user_id": user_id})

    if check.count():
        return True

    else:
        return False

def getCurrentClueNumber(id_number):
    db = MongoClient().users

    check = db.user.find({"user_id": id_number})

    if check.count():
        for item in check:
            return item['clue']

    else:
        return None


def getNextClueNumber(id_number):
    db = MongoClient().users

    check = db.users.find({"user_id": id_number})

    if check.count():
        for item in check:
            if (item['clue'] < 5):
                db.users.replace_one(
                    {"user_id" : id_number},
                    {"user_id" : id_number, "clue": (item['clue'] + 1), "app": "viberhuntbot"}
                )
                return (item['clue'] + 1)
            else:
                db.users.delete_one({"user_id": id_number})
                return 0
    else:
        result = db.users.insert_one({
            "user_id": id_number,
            "clue": 1,
            "app": "viberhuntbot"
        })

    return 1
