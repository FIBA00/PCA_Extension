# Prompt crafter extension version

- idea: when using any ai the extension will listen for the url for known AI websites and checks 
if there is currently input area for prompt and it will take over the search area.
then when user submits the prompt it will send it to the background script and the background script will send it to the content script of the ai website and then the content script will fill the prompt area with the prompt and submit it.

- we can do either forced hijack which means that the extension will take over the search area and the user will have to use the extension to submit the prompt or we can do optional hijack which means that the user can choose to use the extension or not.[but this will stop other ai functions such as inputs and other options to be hidden ]

- also optional input area displayed over the ai website which will allow the user to submit the prompt without taking over the search area and when user sumbits the prompt we process it show it to the user and add ability to copy or edit the returend prompt.