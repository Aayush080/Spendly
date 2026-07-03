---
description : Seed realistic dummy expenses for a specific
user
argument - hint : < user_id > < count > < months >
allowed - tools : Read , Bash ( python3 *)
---
User input : $ARGUMENTS
Step 1 -- Extract from arguments :
- user_id ( integer )
- count ( integer )
- months ( integer )
If any are missing , tell the user the correct format :
/ seed - expense < user_id > < count > < months >
Step 2 -- Verify the user exists in the users table .
If not , abort with a clear error message .
Step 3 -- Generate and insert expenses :
- Spread count expenses across the last months months .
- Realistic amount ranges per category :
* Food : 50 - 800 INR
* Health : 100 - 2000 INR
* Travel : 100 - 3000 INR
* Bills : 200 - 5000 INR
* Shopping : 100 - 4000 INR
Step 4 -- Print a summary of the inserted expenses .