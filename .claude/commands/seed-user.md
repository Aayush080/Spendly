# File : . claude / commands /seed - user .md
---
description : Create a single dummy user in the database
allowed - tools : Read , Bash ( python3 *)
---
You have to read database . py to understand the users table ,
then
write and run a Python script using Bash that generates a
realistic
random Indian user using your own knowledge of common Indian
names .
Fields to generate :
- name
- email
- password ( always "123 ", encoded / hashed before storing )
- created_at ( current timestamp )
Steps :
1. Check whether the generated email already exists in the
database .
2. If it does , generate a new one and retry until unique .
3. Insert the user using the get_db () function .
4. Print out the details of the inserted user .//