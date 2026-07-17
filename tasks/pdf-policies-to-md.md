
I want to provide an ELT transformation process to Opportunity policy pdfs which can be represented as markdown inside HTML. The party wants to provide details of their policy documents from their website without providing the pdfs via web-server hosting.

TODO: provide a mermaid.ai diagram below to explain the transformation process (exclude dagster explaining it broadly):


This means I need you to:

* Identify the policy documents that need to be covered.
* Ensure they are up-to-date
* Apply the conversion to markdown
* Use the pdfs skill to validate that policy content matches what is in the pdf.
* Provide any improvements possible in current/additional ELT processing stages.

Specific requirements:

* Provide a target output directory for each policy document as htmls
* Provide a report on which additional changes were needed
* Validate via tests that the content marries between pdf and md / html output.
* Comment on any other challenges within the process

Ask me questions for clarification and include decisions below...


## Process

Policy detail PDFs from opportunity.org.nz (hosted on Google Drive) flow through a parallel pipeline alongside the scraped HTML — downloaded, extracted as structured markdown, validated, and rendered as HTML. Source PDFs are never served; only the extracted content reaches the site. See [`docs/pdf-extraction.md`](docs/pdf-extraction.md) for the full process (tools, output paths, two-pass validation, and where to find the content for hosting on opportunity.org.nz). The per-PDF coverage report lives at [`docs/pdf-pipeline.md`](docs/pdf-pipeline.md).

## Rationale

This is to update the oppertunity party website adding the html documents into the party's marketing campaign website. 

I need a structured workflow to work through all of the documents to manually review that they are correct. Can you help expand the list below.

## Validation Stages

I follow a manual validation process
[[docs/screenshots/11-manual-qa-policy-documents.png]]. I need to apply this to all policy docs.

- [ ] Tax Reset
- [ ] ... TODO list all pdfs.

Validation includes visualising the policy markdown to html documents, making sure they match the pdfs, and pass basic html validation. 

- [ ] Tax Reset
- [ ] ... TODO list all html docs.

## Presentation

I need to create a set prepare a set of PRs for merging into the website. For now, can you collect and list all of the documents I need per pdf.

This should include:

- The constitution / policy website page which holds the Google Drive link which needs to be updated to include an pdf -> md -> html document reference.
- The pdf, md, and html documents in reference to this repo as markdown. This should be directly auditable for me. I will look to develop a template to create structured PRs from this later. 


### Tax Reset

* Google Drive: 
* Website page:
* pdf: 
* md: 
* html:




