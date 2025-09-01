# TODO: Add Mobile Number to Registration and Login

- [x] Update templates/register.html: Add mobile number input field after the email field with 10-digit validation.
- [x] Update app.py /register route: Retrieve mobile from form, check uniqueness, save to user data.
- [x] Update templates/login.html: Change email field label to "Email or Mobile Number" and input type to "text".
- [x] Update app.py /login route: Use single identifier to find user by email or mobile.
