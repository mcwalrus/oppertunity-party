# Agent Approach

I want *firecrawl* to be seperate to the dagster framework. The reason is that I don't want to do this every time I ask to materialise the repo. It would be good to work with the results to see if this is the case.

Configure all the information for using firecrawl within this website. Provide a readme which explains what firecrawl does. Primarily we want to use it for crawling and downloading the website. This is so we can compare it with the results from our other project.

The output should create `llms.txt` and `llms-full.txt` as a listed command using the native `firecrawl` cli command. This is the main point of the library which I am trying to understand.  

As far as I know, there is no real schema for `llms.txt` and `llms-full.txt` as it seems to be an non-standardised schema. Formatting will help but agents will still understand it. This folder will manage the output from the firecrawl results against the <https://www.opportunity.org.nz/> site.

/Users/max.collier/Desktop/Screenshot\ 2026-06-14\ at\ 2.04.54 pm.png
