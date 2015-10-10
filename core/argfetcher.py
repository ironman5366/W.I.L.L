def main(objectvar, *args):
    args=args[0]
    f = open("core/content/args.txt", 'w')
    content=open("core/content/content.txt").read().split("\n")
    print "object is:"+objectvar
    print "args are:"+str(args)
    for item in content:
        if "Names:" in item:
            if "None" not in item:
                names=item.split("Names:")[1]
            else:
                names=None
        elif "Email" in item:
            if "None" not in item:
                email=item.split("Email:")[1]
            else:
                email=None
        elif "Phone:" in item:
            if "None" not in item:
                phone=item.split("Phone:")[1]
            else:
                phone=None
        elif "Time:" in item:
            if "None" not in item:
                time=item.split("Time:")[1]
            else:
                time=None
        elif "Date:" in item:
            if "None" not in item:
                date=item.split("Date:")[1]
            else:
                date=None
    a=open("core/content/askedargs.txt", 'w')
    for item in args:
        a.write(str(item)+'\n')
    for item in args:
        print "Args item is:"+str(item)
        if item=="object":
            f.write("object="+objectvar+'\n')
        if item=="command":
            f.write("command="+objectvar+'\n')
        if item=="subject":
            if names!=None:
                if "," in names:
                    names=names.split(",")[0]
                    f.write("subject=contact:"+names+'\n')
                else:
                    f.write("subject=contact:"+names+'\n')
            elif email!=None:
                if "," in email:
                    email=email.split(",")[0]
                    f.write("subject=email:"+email+'\n')
                else:
                    f.write("subject=email:"+email+'\n')
            elif phone!=None:
                if "," in phone:
                    phone=phone.split(",")[0]
                    f.write("subject=phone:"+phone+'\n')
                else:
                    f.write("subject="+email+'\n')
            else:
                f.write("subject=None\n")
        elif item=="phone":
            if phone!=None:
                if "," in phone:
                    phone=phone.split(",")[0]
                    f.write("subject=phone:"+phone+'\n')
                else:
                    f.write("subject=phone:"+phone+'\n')
            else:
                f.write("subject=phone:None\n")
        elif item=="email":
            if email!=None:
                if "," in email:
                    email=email.split(",")[0]
                    f.write("subject=email:"+email+'\n')
                else:
                    f.write("subject=email:"+email+'\n')
            else:
                f.write("subject=email:None\n")
        elif item=="time":
            if time!=None:
                if "," in time:
                    time=time.split(",")[0]
                    f.write("time="+time+'\n')
                else:
                    f.write("time="+time+'\n')
            elif date!=None:
                if "," in date:
                    time=date.split(",")[0]
                    f.write("time="+date+'\n')
                else:
                    f.write("time="+date+'\n')
            else:
                f.write("time=None\n")
        #TODO: Here would be the place to add a call to an accounts module



