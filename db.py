from pymongo import MongoClient

db = MongoClient().users

id_number = 4373737373

#print "inserted [{}].".format(result.inserted_id)



check = db.users.find({"user_id": id_number})

if check.count():
    for item in check:
        if (item['clue'] < 5):
            db.users.replace_one(
                {"user_id" : id_number},
                {"user_id" : id_number, "clue": (item['clue'] + 1), "app": "viberhuntbot"}
            )
            print 'updated clues for user %s to %s'%(id_number,(item['clue'] + 1))
            print (item['clue'] + 1)
        else:
            db.users.delete_one({"user_id": id_number})
            print 'finished'
else:
    result = db.users.insert_one({
        "user_id": id_number,
        "clue": 1,
        "app": "viberhuntbot"
    })

    print 'inserted %s into the DB'%(result.inserted_id)
