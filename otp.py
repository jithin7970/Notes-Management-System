import random as r
import string
def genotp():
    otp=''
    for i in range(2):
        otp+=r.choice(string.ascii_uppercase)
        otp+=str(r.randint(0,9))
        otp+=r.choice(string.ascii_lowercase)
    return otp