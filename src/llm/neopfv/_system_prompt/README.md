# Installation (first time)
ChatGPT AutoExpert (Developer Edition) is intended for use in the ChatGPT web interface, and with a Pro subscription. To activate it, you'll need to do a few things!

1. Download the [latest release](https://github.com/spdustin/ChatGPT-AutoExpert/releases/latest)
    - Expand **Assets**, then download the file titled "**Source Code** (zip)"
2. Extract the downloaded .zip file
3. Sign in to [ChatGPT](https://chat.openai.com)
4. Select the profile + ellipsis button in the lower-left of the screen to open the settings menu
5. Select **Custom Instructions**
    > [!WARNING]
    > You should save the contents of your existing custom instructions somewhere, because you're about to overwrite both text boxes!
6. Copy and paste the text from [`developer-edition/chatgpt__about_me.md`](https://raw.githubusercontent.com/spdustin/ChatGPT-AutoExpert/main/developer-edition/chatgpt__about_me.md) to the first text box, replacing whatever was there
7. Copy and paste the text from [`developer-edition/chatgpt__custom_instructions.md`](https://raw.githubusercontent.com/spdustin/ChatGPT-AutoExpert/main/developer-edition/chatgpt__custom_instructions.md) to the second text box, replacing whatever was there
8. Select the **Save** button in the lower right
9. Continue with the per-chat installation steps
# Installation (per-chat)

1. Start a new chat
2. Select **GPT-4** at the top of the new chat
3. Select **Advanced Data Analysis** from the menu
4. Attach `autodev.py` by selecting the **(+)** button to the left of "Send a message" at the bottom of the chat
5. Without entering any other text in the input text box, select the paper airplane icon to send the empty text and upload the `autodev.py` file
6. If all went well, you should see a heading "ChatGPT AutoExpert (Developer Edition)" along with an introduction to the tool
