import random

def guess_number():
    number = random.randint(1, 100)
    attempts = 0

    print("🎯 Welcome to the Number Guessing Game!")
    print("I'm thinking of a number between 1 and 100.\n")

    while True:
        try:
            guess = int(input("Your guess: "))
            attempts += 1

            if guess < number:
                print("📉 Too low! Try higher.\n")
            elif guess > number:
                print("📈 Too high! Try lower.\n")
            else:
                print(f"🎉 Correct! You guessed it in {attempts} attempt(s)!")
                break
        except ValueError:
            print("⚠️  Please enter a valid number.\n")

guess_number()