# TODO: Update Conversation Messaging System

## Steps to Complete

- [x] Edit templates/store.html: Update "Contact Seller" link to use 'conversation_start' route
- [x] Edit templates/inbox.html: Update conversation links to use 'conversation_chat' with convo_id
- [x] Edit templates/conversation.html: Update form action to use 'conversation_chat' with convo_id (already correct)
- [x] Edit app.py: Add new routes (conversation_start, conversation_chat already present)
- [x] Edit app.py: Add /inbox route to sort conversations by latest message timestamp
- [ ] Test the updated conversation flow to ensure no regressions
