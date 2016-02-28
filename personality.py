from datetime import datetime
import random


def get_greet(f):
    '''
    Input: Salutation type ('hello', 'goodbye', etc.)
    Output: Random relevent string
    '''
    # Get time and determine environmental variables
    polite_tolerance = 3
    humor_tolerance = 3
    hour = datetime.now().hour
    if hour < 12:
        lt = "Morning"
    elif hour > 17:
        lt = "Night"
    else:
        lt = "Afternoon"

    # Open the file with the string to output and open the personality txt
    # No verification of either files, the program trusts that the data
    # is formatted correctly.
    greetings = open("personality.txt").read().split("\n")
    file = open("output.txt").read().split("\n")
    polite = int(file[0].split("polite=")[1])
    humor = int(file[1].split("humor=")[1])
    phrase_array = []

    # I have no clue about his section, I really hate myself for writing it. It's awful I know and just the worst. I have no idea why it works.
    # For each greeting line, the appropriate time ('Morning', 'Neutral', etc.)
    # is selected and a range of greetings that match the politeness and humor within 2 values.
    # From the list of possible greetings, one is selected randomly.
    #
    # Format for personality.txt: 'Phrase:Time,polite=x;humor=x/f=salutation'
    for greet in greetings:
        try:
            class_list = greet.split(':')[1].split(",")
            phrase = greet.split(":")[0]
            if class_list[0] == lt or class_list[0] == "Neutral":
                values_list = class_list[1].split(";")
                polite_val = int(values_list[0].split('polite=')[1])
                if polite in range(polite_val - polite_tolerance,
                                   polite_val + polite_tolerance):
                    humor_val = int(values_list[1].split("/")[0].split("humor=")[1])
                    if humor in range(humor_val - humor_tolerance,
                                      humor_val + humor_tolerance):
                        salutation = values_list[1].split("/")[1].split("f=")[1]
                        if salutation == f:
                            phrase_array.append(phrase)
                        else:
                            pass
                    else:
                        pass
                else:
                    pass
            else:
                pass
        except IndexError:
            pass
    finalout = random.choice(phrase_array)
    return finalout

# A small test
if __name__ == "__main__":
    f = "hello"
    neutral_greeting = get_greet(f)
    print("Neutral: " + neutral_greeting)
