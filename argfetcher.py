

def get(objectvar, command):
    '''Gets required arguments from content.txt'''
    args = args[0]
    f = open("args.txt", 'w')
    content = open("content.txt").read().split("\n")
    names = ['Names', 'Email', 'Phone', 'Time', 'Date']
    for item in content:
        if "Names:" in item:
            if "None" not in item:
                names = item.split("Names:")[1]
            else:
                names = None
        elif "Email" in item:
            if "None" not in item:
                email = item.split("Email:")[1]
            else:
                email = None
        elif "Phone:" in item:
            if "None" not in item:
                phone = item.split("Phone:")[1]
            else:
                phone = None
        elif "Time:" in item:
            if "None" not in item:
                time = item.split("Time:")[1]
            else:
                time = None
        elif "Date:" in item:
            if "None" not in item:
                date = item.split("Date:")[1]
            else:
                date = None
        if objectvar == "name":
            if "," in names:
                names = names.split(",")[0]
                return names
            else:
                return names
        elif objectvar == "email"
            if "," in email:
                email = email.split(",")[0]
                return email
            else:
                return email
        elif objectvar == "phone":
            if "," in phone:
                phone = phone.split(",")[0]
                return phone
            else:
                return phone
        elif objectvar == "time":
            if "," in time:
                time = time.split(",")[0]
                return time
            else:
                return time
        elif objectvar == "date":
            if "," in date:
                date = date.split(",")[0]
                return date
            else:
                return date
        # TODO: Here would be the place to add a call to an accounts module
