# Storytime

A little Flask-based LLM-backed story generator for my kids, hosted on an Raspberry Pi so anyone in the house can access it from their mobile devices.

Absolutely not ready for production but "works on my machine".

I run Ollama at home on a beefy desktop with some big models on it, so when my desktop is on this app talks to Ollama to locally/privately generate stories. If my desktop isn't turned on, the integrated API-chooser means we can optionally select Mistral/Anthropic/OpenAI as alternate generation sources if we want to.

Also optionally generates images using OpenAI image generation, then inserts them at the end of the story.

![Storytime Screenshot](https://github.com/obsoletenerd/Storytime/blob/main/StorytimeScreenshot.png?raw=true)

## TODO
- [x] Check which API keys are present, and if Ollama is running, then only show valid options for LLM choice in pulldown
- [ ] Fix the templates to work better on mobile
- [ ] Try and find a small model that works well enough on an RPi just for the text generation for better privacy when run off the Pi
