
If you've ever played a video game on a computer, chances are you've used or heard of Steam. Launched in 2003 to distribute game studio Valve's own games, but later expanded to become a storefront for video games from third party developers, Steam became so wildly successful that today Valve practically gave up making its own games. Steam became so dominant in the space by the mid-2010s that even a few major studios splitting off and making their own launchers hardly seemed to matter, and in recent years some of those same studios (EA, for example) have come back to Steam, because that's where the money is. In 2013, for example, [one source](https://www.bloomberg.com/news/articles/2013-11-04/valve-lines-up-console-partners-in-challenge-to-microsoft-sony) had Steam pegged at a whopping 75% market share. 

[Statistia](https://www.statista.com/topics/4282/steam/#topicOverview) estimates that even today Steam remains a behemoth, with over 10,000 new games in a single year and peaking at 10 billion dollars in revenue! The path to this windfall: taking a 30% cut from every sale on the platform, making Valve the ultimate PC gaming middle man. Cue a challenge. Epic, both maker of popular game engines that power game graphics and physics, and publisher of smash 2017 hit Fortnite (itself estimated to have brought in [20 billion](https://www.tweaktown.com/news/94476/fortnite-made-over-20-billion-in-revenue/index.html) dollars in lifetime revenue), decided to follow a similar path, and expanded their own launcher to sell third-party games. The pitch? [Only a 12%](https://www.gameinformer.com/2018/12/04/tim-sweeney-answers-questions-about-the-new-epic-games-store) cut for Epic. At the end of 2018, this expanded storefront went live. 

**The problem?** Change was great for developers, but many users had racked up tons of games and didn't really care to switch. But what DO gamers quite like? **Free stuff.**

As an incentive to pick up and get locked into the platform and corresponding game launcher, Epic started partnering with all kinds of game developers (offering them usually a lump payout) to offer free games for limited times on the storefront. They started out with a bang, giving away popular indie game Subnautica, and then every two weeks came out with something new. This actually accelerated, and in June 2019 they upped this to a game every week... and sometimes two! Astonishingly, this continues to this day, making over five years of giveaways. Occasionally, a game is given away again months or years later, but other games are completely new. Across this time period, there have been over 400 giveaways!

Clearly, this is a lot of games, and something I felt would be very interesting to look at. Some of these were big games, too. Grand Theft Auto V was given away, brought over [7 million](https://www.theverge.com/2021/8/19/22631952/epic-games-store-gta-v-free-game-7-million-new-users-apple-trial) new users, and crashed Epic's servers by itself, for example. 

<figure>
	<img src="{{site.url}}/{{site.baseurl}}/assets/img/TopReddit.png" alt=""> 
	<figcaption>The most-hyped games given away according to reddit posts in a subreddit for gaming deals</figcaption>
</figure>

#### Collecting some data

Thankfully, I'm not the only one interested in these games. For my data collection, I noticed that there was a nicely formatted list found [here](https://www.steamgifts.com/discussion/S4e2c/free-epic-games-store-list-of-all-weekly-free-games-every-thursday-at-11-am-et). Others have looked into repeat games, but there's a lot of other information that I haven't seen anyone else look into. For example, what kinds of genres? How many different developers/publishers worked with Epic? How many dollars worth of games were given away? What kind of ratings were the games given, are they all well-reviewed hits or is the list full of shovelware?

Examining *how* I collected this data, I hope, can be helpful to others in a similar situation who want to take another step, and acquire and analyze their own data for a similar kind of question. 

I should state that there are about a half dozen lists floating around by various websites and users with about the same amount of data, probably in turn scraped from Epic's homepage or news sources. I chose this list in particular because it also offered links to each store page, which I felt could be very helpful. However, other than name and date, the list isn't very populated. My first step was to simply get this data myself, in a good format. Web scraping to the rescue!

Load up some typical packages and grab the table:

```python
import pandas as pd             # data manipulation package
import numpy as np              # common companion to pandas
from bs4 import BeautifulSoup   # to make sense of scraped hmtl
import requests                 # to obtain the data via scraping
import re                       # to parse and manipulate text
import time                     # to obey any rate limits

gameurl = "https://www.steamgifts.com/discussion/S4e2c/free-epic-games-store-list-of-all-weekly-free-games-every-thursday-at-11-am-et"
r = requests.get(gameurl)
r.status_code  # 200 = good!

gsoup = BeautifulSoup(r.text)
gtable = gsoup.find("table")
gdf = pd.read_html(str(gtable))[0]
gdf.reset_index()
gdf
```

This part worked great - until I realized it didn't have the links I really wanted. Rats.

#### Common problem solving

Yes, if you're a post-2022 programmer, you sometimes learn to lean on ChatGPT. You might know how to do something but it's often faster to modify something it gives you. And that's what I set out to do. I decided to just grab the links separately and then mash the dataframes together after. I got some code and tweaked it. This was the result:

```python
table_rows = gtable.find_all('tr')
links = []
for tr in table_rows:
    td = tr.find_all('td')
    for cell in td:
        link = cell.find('a')
        if link:
            links.append(link['href'].strip())
links_series = pd.Series(links1)

gdf["Link"] = links_series
print(gdf)
```

Moral of the story? If it's your own project, your time matters and getting a little help is okay. Perhaps it's a bit messier than it needs to be, but it works just fine and it's still readable. ChatGPT is a great choice of helper I would encourage you to use if you briefly get hung up on one part, or just to save time. I should also mention that in this case, it seems pretty straightforwardly ethical to grab this data. It's public, it's commonly available information, and I'm going to be crediting them in my similarly public code publishing at the end of the project. 

#### Using an API to enrich the data

At this point the original goal still stands: I want to add some color to the dataset, and enrich it to answer my original questions. The Epic Games Store itself is probably the best resource for this, as some of the games in the free giveaways are exclusive to Epic and thus can't be found elsewhere. Also, prices can vary from storefront to storefront.

While I had first planned on using Selenium or a similar tool to scrape data from each webpage individually, I soon landed on a more efficient solution: Using an API. Sadly, though Epic offers **a lot** of API support, most of it is directed at game developers, not random people scraping store listings. Thus, their extensive documentation wasn't much help. A wrapper for the store API, however, was open source and available, `epicstore-api`, located on PyPI [here](https://pypi.org/project/epicstore-api/) with a sparse but useful [documentation](https://epicstore-api.readthedocs.io/en/latest/). 

It took a little playing around, but I settled on a script that would grab a page's information and make sense of the right things in the JSON it returns:

```python
import epicstore_api
from epicstore_api import EpicGamesStoreAPI, OfferData
import json

api = EpicGamesStoreAPI()
def get_gamedata(gamename, tries = 10):
    # takes a string gamename, searches for it, finds exact match
    # returns dict with id, descr[iption], namespace, orig[inal]_price, fmt_orig_price (nicely formatted), and tags

    dict = api.fetch_store_games(count = tries, keywords = gamename)
    match = None
    for element in dict["data"]["Catalog"]["searchStore"]["elements"]:
        if element["title"] == gamename:
            match = element
            break
    to_return = {
    "id": match["id"],
    "descr": match["description"],
    "namespace": match["namespace"],
    "orig_price": match["price"]["totalPrice"]["originalPrice"],
    "fmt_orig_price": match["price"]["totalPrice"]["fmtPrice"]["originalPrice"],
    "tags": match["tags"],
    "seller": match["seller"]["name"]
    }
    return to_return

# Create a quick function wrap that waits between each requests and backfills with blank data if failed
def single_get(name):
    time.sleep(.5)
    try:    
        done = get_gamedata(name)
    except:
        try:
            done = get_gamedata(name, 100)
        except:
            done = None
        done = None
    return done

# get everything (will take a while!!)
data_return_df = [single_get(a_game) for a_game in gdf['Name']]
```

I want to quickly mention three things about this: One, looking for an API and a wrapper saved me a lot of time and let me get quick results. Second, starting with one game, and the basic info, was very helpful; waiting until later to add complexity let me be efficient. There are still a few tweaks I want to make and more information to grab, but having data ready to go is very encouraging. Finally, to use best practice and avoid errors from flooding the server, I implemented both a wait between each game (in my case, to grab at most 120 games per minute, probably less due to python processing time) and also only fell back on grabbing more search results in the initial matching process if necessary (most games had one match, but a few with generic titles needed more). This is just being a good "scraping citizen".

#### Future work

So, now I have a nice list of game tags, which are the genres for each game, the pricing, the sellers, and other information to get further data if I so choose (like reviews or other information from the webpages) on top of the original information including the release dates. I posted only a few snippets of code from my larger script just to illustrate the general approach, but there was obviously some more things going on too, like better name matching and further information gathering.

Stay tuned for an upcoming post in the next few weeks where I look at the data and find out patterns with repeats, explore what kinds of games are being given away, and answer the burning question: **Just how many dollars worth of games have been given away?** If there's another curiousity you have about these free games, please drop a comment or send me an email!


<!-- If you're seeing this post, you're ahead of the curve! Stay tuned for the next update, on a project to collect data about Epic's five-year free game giveaway experiment of over 400 games via web scraping and APIs. -->

<!-- Intro about Steam's dominance, a chart about that dominance

(also: Potential data or charts from various Epic Game Store Year in Review posts, aggregated?)

Story about EGS free games and their efforts, including biggest giveaways

Get down to brass tacks: explain initial list scraping and desire for more data

Problems faced trying to scrape links themselves

Solution (mostly): use wrapper for API (how much detail??), focus on thought process I think

(Optional) Problems faced with age restrictions, empty rows

Conclusion, hype for follow-up data, desire to fill in empty bits (Selenium?) -->