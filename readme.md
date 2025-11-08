Hey, let's do a bit of brainstorming for a new project that I have in mind. We'll summarize this in a document to serve as our north star for ideation and development

Problem statement: LLMs are often used for translation tasks, and one of the more obvious cases that they do way better than everything else is translation of literature, novels for instance. Previous machine translation-based approaches have had relatively poor quality, capturing perhaps the meaning of the word, but not necessarily the style and phonetic sense of the word.

However, simply feeding in copy-paste text into ChatGPT is a poor user experience.

The same novel may have been translated multiple different times under multiple different prompts, resulting in wasted compute.
The manual copy-pasting of things is painful.
Here we seek to resolve this by having a platform that does the following:

It will have LLM integrations that work on standardised extracted corpora. For example, we would have a scraper that integrates with certain sites, is able to pull down the information, and then perform translations.
We will provide tools for helping with the management of the translations. For example, prompts, prompt versions, and result and output.
Using the above two, we can store the generated data, allowing us to make versioned translations of a given novel without excessive compute, and with a clear chain of provenance
I will now list out at least some core features and some core targets:

The target here would be the Japanese language, focusing on novels. The Japanese have a very rich fanfiction and independent fiction community that we can then which have with open data sets.
Users will be allowed to write prompts and store them.
Prompts can then be used to generate translations of certain novels, and also the generated translations will be linked to said prompt at its particular point in time. Note that you could have a final translation that integrates different translation fragments at every point from different prompt versions at different points in time. This is to prevent having to recompute the entire chunk of text every time a prompt is updated.
A sample user experience will look like this:

The user first identifies a book that they want. Our integrations will then be able to go through, identify chapters, and start pulling down this information.
The user writes a prompt, saves the prompt. The user then begins a translation attempt using a selected prompt, a novel and a specified number of chapters or perhaps specified length of text.
We then generate line-by-line translations, that is to say contrasting the original text against the translated text, allowing bilingual users to be able to use this as a translation tool as well.
The user is able to then eventually retrieve both the single translation as well as the combined original text and translation.
So now having this, let's summarise this and brainstorm as to what we want to do here and what we might be missing.