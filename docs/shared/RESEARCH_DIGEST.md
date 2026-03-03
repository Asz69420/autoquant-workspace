# Research Digest

> Trading concepts extracted from YouTube videos and TradingView research.
> Updated automatically. Quandalf reads this each cycle for strategy inspiration.
> This is a rolling digest — oldest entries drop off as new ones arrive.

**Last updated:** 2026-03-03 02:01 UTC
**Entries:** 25

---

## 1. strategy_004_gaussian_channel_trend_pullback
*manual-transcript-drop | transcript_drop | 2026-02-26*
Source: transcript_drop://strategy_004_gaussian_channel_trend_pullback

**Summary:** STRATEGY: Gaussian Channel Trend Pullback (Approximation) ASSET: BTC, ETH TIMEFRAME: 4h (primary), also test on 1h MARKET CONDITION: Established trends with healthy pullbacks TYPE: Trend pullback (buy the dip / sell the rip) CONCEPT: Inspired by Gaussian channel strategies that perform well on BTC. A Gaussian channel is essentially a heavily smoothed moving average with deviation bands that identify trend direction and pullback zones. We approximate this using EMA with Bollinger-style ATR bands. The key insight is: in a strong trend, pullbacks to the lower channel band are buying opportunities, not reversals. We combine with Stochastic to time entries precisely when the pullback is exhausted and momentum is turning back.
**Trading Rules:**
- We combine with Stochastic to time entries precisely when the pullback is exhausted and momentum is turning back.
- ADX > 20 EXIT RULES: - Take profit: Price reaches opposite channel band (upper band for longs, lower for shorts) - Stop loss: Price closes beyond the channel band on entry side (below lower channel fo
**Strategy Components:**
- [trend] STRATEGY: Gaussian Channel Trend Pullback (Approximation) ASSET: BTC, ETH TIMEFRAME: 4h (primary), also test on 1h MARKET CONDITION: Established trends with healthy pullbacks TYPE: Trend pullback (buy
- [trend] A Gaussian channel is essentially a heavily smoothed moving average with deviation bands that identify trend direction and pullback zones.
- [trend] The key insight is: in a strong trend, pullbacks to the lower channel band are buying opportunities, not reversals.
- [momentum] We combine with Stochastic to time entries precisely when the pullback is exhausted and momentum is turning back.
- [momentum] Stochastic K crosses above D from below 20 (pullback exhausted, momentum returning) 5.
- [risk] Stop: below previous swing low.
**Risk Management:**
- Stop below previous swing low.
**Entry/Exit Conditions:**
- ADX > 20 EXIT RULES: - Take profit: Price reaches opposite channel band (upper band for longs, lower for shorts) - Stop loss: Price closes beyond the channel band on entry side (below lower channel fo
**Indicators:** EMA, ATR, Stochastic, ADX
**Context:** Timeframes: 4h, 1h | Assets: BTC, ETH

---

## 2. Best AI Trading Bots of 2026? My Plan for AI. (INSANE Profit)
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=jUJ0tMsHm1M

**Summary:** Okay, let me take you back to January 2025. CryptoBanta kindly invited me to be a host as their bot expert on their main channel. And very quickly, one topic took over the room. Bots vs humans, who would actually win? So they put me on the spot.
**Trading Rules:**
- I use ADX to stay out of markets when they go sideways.
- And that's it, simple rules, automated execution.
- They don't use the same logic and I'm very careful not to stack risk and I do my best to spread it.
- Yes, I have a system to know when to turn off a bot.
- Yes, I know it's a bit like when you're holding Bitcoin and you can feel it going down and you're trying to catch those lower lows.
- The problem is, is that when markets do plummet, you just end up buying, buying, buying and eventually getting liquidated.
- We can diversify, set stop rules and we can use AI responsibly to actually help us trade better.
**Strategy Components:**
- [trend] They're simple trend following systems that I do and build here live on YouTube every single week.
- [trend] I use simple tools like a Trendilio indicator for entries.
- [trend] I use a T3 for trend direction.
- [risk] They don't have the same stop losses and they certainly don't have the same way of taking profit.
- [risk] They don't use the same logic and I'm very careful not to stack risk and I do my best to spread it.
- [risk] In December, my account dropped by 11%, which was extreme pain for myself.
**Risk Management:**
- Stop below previous swing low.
- Apply 1% risk rule.
**Entry/Exit Conditions:**
- They don't use the same logic and I'm very careful not to stack risk and I do my best to spread it.
**Indicators:** ADX
**Context:** Timeframes: weekly, daily

---

## 3. This Smart Money Indicator Looked Too Good to Be True... I Tested It
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=YvGITxuf7zg

**Summary:** Today, we're going to be backtesting this popular smart money indicator on trading view. It was sent to me by my community. It looks amazing on a chart. But does it actually really make any money? Well, I can tell you one little secret actually changed everything.
**Trading Rules:**
- This one here, if you were to hit it, would have managed to get you about 8% and they generally seem to pop up quite well.
- There's some real rules behind the actual strategy by adding another indicator for stoplosses and take profits.
- Okay, so these are the rules of the strategy.
- I'm going to add a couple of indicators for confluence and we're going to see if we can make this any better.
- Okay, guys, I've come up with a new set of rules for this strategy.
- When price is above the range filter, it is green and not gray like this here.
- We're looking for longs and when it's pink and prices below it, we're looking for shorts.
- And this is how we set our stop loss and take profit.
**Strategy Components:**
- [momentum] First of all, we have a momentum indicator that checks price change and then make sure that that price change goes over a threshold.
- [trend] We then have an anti-spam filter meaning that we will not be taking hundreds of chains all in the same trend one after the other and we will put a distance between each and every trade.
- [trend] Next, we have a trend direction.
- [filter] We have a volume filter that allows us to make sure that we're not getting into trades where there's no volume at all.
- [filter] We then have an optional breakout filter.
- [filter] By adding the range filter, it allows us to filter out some of these bad trades.
- [risk] ATR bands allowing us to set our stop losses and take profits.
- [risk] And this is how we set our stop loss and take profit.
- [risk] So if the stop loss is too far away you either cancel that trade or you use a percentage instead.
**Risk Management:**
- Stop below previous swing low.
**Entry/Exit Conditions:**
- And this is how we set our stop loss and take profit.
- So if the stop loss is too far away you either cancel that trade or you use a percentage instead.
- This will keep you out of huge trades with huge stop losses that never ever either hit the stop loss or take profits.
- We're going to set our first long entry on the candle setting the stop loss directly to the ATR band and looking for a take profit of one to 1.5 and boom.
- I actually thought it was going to hit the stop loss before not so bad.
- The stop loss is actually huge.
**Indicators:** ATR

---

## 4. TRADER REVIEW: The " ONE CANDLE " Scalping Strategy I Will Use For Life @The Rumers
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=tzXWPcf-GM4

**Summary:** This trader here says that one single indicator is enough to become a profitable trader and that indicator is the nine exponential moving average. And listen, I suggest you stay until the end because yes, this strategy looks a little bit too simple to be profitable, but when backtesting, the data did something that I just didn't expect. Okay, guys, here we are on YouTube. This is the YouTube channel I was talking about. I've been through this strategy and pretty anything seems very, very simple.
**Trading Rules:**
- And listen, I suggest you stay until the end because yes, this strategy looks a little bit too simple to be profitable, but when backtesting, the data did something that I just didn't expect.
- So in this video, you're going to be getting the exact rules of the strategy, the exact variations because there are three and the backtesting results, no discretion, no cherry picking, and the twist 
- So when that price is below the EMA like it is currently at the moment and then breaks over, this is where we're going to be looking to take a long, very, very simple.
- We'll take a long on the following candle after it actually breaks out without any stop loss.
- We're going to be actually using the EMA as our stop is going to be our stop loss and also our take profits.
- When price goes below the EMA like that, we can either stay out of the market and only accept longs or what we can do is we can actually short the market at this point here as price crosses below, we 
- So if we go back over to our first long entry here, this is where we would have got in or on the retest.
- We would still not have any stop loss, which in my eyes makes this one a little bit more risky because we don't even have the EMA protecting us if price continues to dump.
**Strategy Components:**
- [risk] We'll take a long on the following candle after it actually breaks out without any stop loss.
- [risk] We're going to be actually using the EMA as our stop is going to be our stop loss and also our take profits.
- [risk] So maybe a little bit less risky, allowing us to retest that EMA, just making sure that we don't get chopped in and out of entries as price does tend to come back to the EMA quite often.
- [trend] Once we've retested, we'll be able to take our entry there, just giving us a little bit of time to confirm that we are actually in a trend.
**Risk Management:**
- Stop below previous swing low.
- Apply 1% risk rule.
**Entry/Exit Conditions:**
- We'll take a long on the following candle after it actually breaks out without any stop loss.
- We're going to be actually using the EMA as our stop is going to be our stop loss and also our take profits.
- When price goes below the EMA like that, we can either stay out of the market and only accept longs or what we can do is we can actually short the market at this point here as price crosses below, we 
- So if we go back over to our first long entry here, this is where we would have got in or on the retest.
- We would still not have any stop loss, which in my eyes makes this one a little bit more risky because we don't even have the EMA protecting us if price continues to dump.
- Now guys do remember this doesn't have a stop loss 22% doesn't mean that you wouldn't have gone even further down it's just that we would have hit that to EMA at 22% and that would have been the maxim
**Indicators:** EMA

---

## 5. I Turned a FREE TradingView Indicator Into a Real Strategy… The Test Shocked Me
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=jBkCq0DnHQU

**Summary:** This very strange indicator has a 63% win rate, but what's weird about it is it only allows you to trade above the line. So guys, I'm going to be converting this into a trading strategy with rules so you can follow along. But for us to do that, we're going to have this start right now. Okay, guys, here I am on trading view. This is the new strategy called Managing Cloud.
**Trading Rules:**
- So guys, I'm going to be converting this into a trading strategy with rules so you can follow along.
- It helps us to keep out of these sideways moving sort of choppy movements and tells us when we can actually trade.
- For example, this one here actually will only tell us when we're allowed to trade.
- When the green line is above zero and red is below zero, we're looking for longs.
- And when it's the other way round, we're looking for shorts.
- The ATR bands adapt perfectly to price movement and just gives us enough wiggle room to have a good stop loss and know exactly when we're going to get out of the market.
- That gives us enough wiggle room to set our stop loss to the ATR bands.
- We're going to set our stop loss to the ATR bands and we're looking for a risk to reward of one to two.
**Strategy Components:**
- [trend] So the next indicator we're going to add is going to give us our trend direction on a much lower timeframe so we know which way to trade.
- [trend] Our third indicator that we're going to be adding is going to be called the Le Mans Trend indicator by David Tech.
- [filter] So we're going to add the Range Filter.
- [filter] The Range Filter by Donovan Wall is just this one here.
- [filter] And thanks to Donovan Wall's Range Filter, we know we're allowed to take an entry here long and pick up movements just like this.
- [risk] But we all know we'd be completely lost without the wonders of the ATR to set our stop losses and take profit.
- [risk] The ATR bands adapt perfectly to price movement and just gives us enough wiggle room to have a good stop loss and know exactly when we're going to get out of the market.
- [risk] That gives us enough wiggle room to set our stop loss to the ATR bands.
**Risk Management:**
- Stop below previous swing low.
- Apply 1% risk rule.
**Entry/Exit Conditions:**
- The ATR bands adapt perfectly to price movement and just gives us enough wiggle room to have a good stop loss and know exactly when we're going to get out of the market.
- That gives us enough wiggle room to set our stop loss to the ATR bands.
- We're going to set our stop loss to the ATR bands and we're looking for a risk to reward of one to two.
**Indicators:** ATR
**Context:** Assets: BTC

---

## 6. A Subscriber Sent Me This FREE TradingView Indicator… I Gave It $10,000 to Test
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=_kvEItHHhJc

**Summary:** I found this brand new trading view indicator that provides a biocell signals and I gave it $10,000 to back test it as far as we possibly can so that you guys can add this strategy to your trading plan but for us to do that we're gonna have to start right now okay guys we're gonna go straight over to trading view first things first I'm gonna give credit where credit is due I found this indicator on the no-nonsense 4x channel they do multiple back tests of these indicators and this is the best in
**Indicators:** for the dmh again and you add the version by valor you can see that they, for atr bands by david tech this one just here we

---

## 7. My Community Found a FREE TradingView Indicator… The Backtest Blew My Mind
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=kSfSp0hZwto

**Summary:** Today, we're going to be testing this indicator here. This was sent to me by my community. It's new and popular on TradingView. But for that to happen, we're going to have to start right now. So guys, here I am on TradingView.
**Trading Rules:**
- So if you've been following me for a while, we all know that having just one indicator on the chart just makes it look pretty.
- I let my system take care of all of my trades from the beginning all the way through the risk management.
- For that, we need to know the rules.
- The rules, as always, with me are known in advance.
- Nobody wants to be chopped in and out of markets like here, where each and every one of our entries are going to get hit the stop loss.
- When price is above it and it is green, we're looking for longs.
- And when price is below and it's orange, we're looking for shorts.
- When it goes above these zero lines here, it goes green and that's when we can take a long.
**Strategy Components:**
- [trend] So the indicator is called the Commodity Trend by BigBuruga, a very popular pine script developer on TradingView in the recent couple of months.
- [trend] It adds not only this area down below, but also adds something that looks a bit like a super trend just above.
- [trend] We're just going to be using the super trend just here.
- [risk] I let my system take care of all of my trades from the beginning all the way through the risk management.
- [risk] Nobody wants to be chopped in and out of markets like here, where each and every one of our entries are going to get hit the stop loss.
- [risk] We're going to set our stop loss to the ATR bands and we're going to set our risk to reward to a 1.5 and boom, we only just about managed to hit the take profit on that one there but it was a winning 
- [filter] We're going to be using the range filter.
- [filter] The range filter by Donovan Wall is an absolutely brilliant indicator as well.
- [filter] We can see the range filter is this indicator here.
**Risk Management:**
- Stop below previous swing low.
**Entry/Exit Conditions:**
- I let my system take care of all of my trades from the beginning all the way through the risk management.
- Nobody wants to be chopped in and out of markets like here, where each and every one of our entries are going to get hit the stop loss.
- When it goes above these zero lines here, it goes green and that's when we can take a long.
- And when it goes below these zero lines here, we go red and that's when we can start thinking about taking shorts.
- When the ADX is above the moving average, we can actually take any long or short positions.
- We're going to set our stop loss to the ATR bands and we're going to set our risk to reward to a 1.5 and boom, we only just about managed to hit the take profit on that one there but it was a winning 
**Indicators:** ATR, ADX

---

## 8. TRADER REVIEW: 1 Minute Scalping Strategy Works Everyday (Stupid Simple and Proven) @Jdub Trades
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=Ntp-o384C5g

**Summary:** This trader here claims that he makes 40k a month last month. I made over $44,000 and in this video, we're gonna be backtesting to see if it actually works But for that to happen, we're gonna have to start right now big bank small bank I like to make money. All right from watching through JDum's trading advice on his YouTube channel I found that he consistently mentions his profitable trading strategy in countless videos If you're trying to find a repeatable and simple trading strategy that you can use every single day to make consistent profits in the market This video is for you reporting that he earns at least $500 a day to $40,000 a month last month. I made over $44,000 now in my experience of running thousands of tests and backtesting over 1,300 strategies these results are not typical and based on benchmarks and the most profitable hedge funds in the world With the best to quants out there This is I can tell you well out of the ordinary and one other thing that absolutely sticks out to me There is extremely low time frame strategy starting on the one minute time frame But I'm certainly not judging. There is only one way to find out if he's telling the truth And that is to sit down all of the rules and code this strategy so that we can backtest it on as much Possible data as I can find Okay, here we are on my computer.
**Trading Rules:**
- I made over $44,000 and in this video, we're gonna be backtesting to see if it actually works But for that to happen, we're gonna have to start right now big bank small bank I like to make money.
- All right from watching through JDum's trading advice on his YouTube channel I found that he consistently mentions his profitable trading strategy in countless videos If you're trying to find a repeat
- There is only one way to find out if he's telling the truth And that is to sit down all of the rules and code this strategy so that we can backtest it on as much Possible data as I can find Okay, here
- There are three strategies But the one that he generally uses is this retest strategy just here So this is the one that I'm actually going to be backtesting today So I'm gonna write down all of the ru
- You can see we have our stop loss and take profit The stop loss is the retested candle which actually come across and broke above And then we're doing a risk to reward of one to two So in the settings
- We can test it on absolutely anything I've set up all of the settings here We can either set our stop loss to the impulse Candle which is this candle here the yellow candle highlighted by yellow here 
- This strategy is absolutely rubbish Okay, guys And there is one thing that I did forget to state and that is that we are actually backtesting here The first strategy which was the breakout and we're u
- So what I'm going to do is now I'm going to check the I'm going to check very quickly the previous day high So if we go here, we can click take profit on previous day high or low That's going to take 
**Strategy Components:**
- [risk] You can see we have our stop loss and take profit The stop loss is the retested candle which actually come across and broke above And then we're doing a risk to reward of one to two So in the settings
- [risk] We can test it on absolutely anything I've set up all of the settings here We can either set our stop loss to the impulse Candle which is this candle here the yellow candle highlighted by yellow here 
- [risk] This strategy is absolutely rubbish Okay, guys And there is one thing that I did forget to state and that is that we are actually backtesting here The first strategy which was the breakout and we're u
**Risk Management:**
- Stop below previous swing low.
**Entry/Exit Conditions:**
- You can see we have our stop loss and take profit The stop loss is the retested candle which actually come across and broke above And then we're doing a risk to reward of one to two So in the settings
- We can test it on absolutely anything I've set up all of the settings here We can either set our stop loss to the impulse Candle which is this candle here the yellow candle highlighted by yellow here 
- This strategy is absolutely rubbish Okay, guys And there is one thing that I did forget to state and that is that we are actually backtesting here The first strategy which was the breakout and we're u
- So what I'm going to do is now I'm going to check the I'm going to check very quickly the previous day high So if we go here, we can click take profit on previous day high or low That's going to take 
- There you go by increasing our stop loss I actually p&l is a lot better, but we're still at minus 31 percent This whizzed through a couple of these other ones here still looking pretty awful to be hon
**Context:** Timeframes: daily | Assets: GOLD, NASDAQ

---

## 9. INSANE New TradingView Indicator Shows Buy & Sell Signals [TESTED]
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=7rianyn0wPI

**Summary:** This brand new buy sale indicator on Trading View looks incredible. It paints perfect entries, and entries and exits are all over the charts. But indicators don't make money, strategies do. So in this video I'm going to be turning this into a real trading strategy, and back to stick properly for at least 100 takes. So you can see that it's actually worth adding to your Trading View chart or just ignoring.
**Trading Rules:**
- The only way to tell is to first this indicator to be part of a system and actually backtest to make sure that the rules are actually good.
- So today I have put together some rules to backtest this strategy here.
- We're going to add a vol or a volatility indicator, and we're going to add the ATR bands for stop loss.
- If I click here, we'll be able to add that directly to the chart.
- The white line is plotted at 0.5, which means that when the green line is above the white line here, we're actually in a trending market.
- This indicator here is going to help us to stay out of markets when we're chopping sideways just like this up here and we don't want to be chit-chopped in and out of the market.
- Now all of these rules put together have started to create us a strategy and not just an indicator.
- We have rules for entries, but entries are nothing without knowing when we're going to get out of our positions.
**Strategy Components:**
- [trend] So we're going to add one for trend direction.
- [trend] Right, this is going to be our confirmation indicator that gets us in and gives us our entries, but we do need a trend indicator that's going to tell us which way the market is going.
- [trend] As you can see, it gives us this pink and lime cloud and a trend line just here.
- [risk] We're going to add a vol or a volatility indicator, and we're going to add the ATR bands for stop loss.
- [risk] That's where we're going to be using ATR bands to be able to set our stop loss and also to project our take profits.
- [risk] What ATR bands actually do is they give us a little bit of a idea of the volatility in the market and allow us to set better stop losses.
- [filter] So for that, we're going to be adding the range of filter, which is by Donovan wall.
- [filter] So first of all, we're going to be looking at the range filter.
- [filter] The range filter has gone green and price is above it just here.
**Risk Management:**
- Stop below previous swing low.
**Entry/Exit Conditions:**
- We're going to add a vol or a volatility indicator, and we're going to add the ATR bands for stop loss.
- That's where we're going to be using ATR bands to be able to set our stop loss and also to project our take profits.
- So we're going to set our first long entry to this candle here and we're going to set our stop loss to the ATR bands.
- And then finally, we're going to be looking for the money, we're going to be setting our risk to reward to 1.5.
**Indicators:** ATR
**Context:** Timeframes: daily | Assets: GOLD

---

## 10. Crypto Trading Made Super Easy!
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=t9v32eQ5qcE

**Summary:** So if you're like me and absolutely love spending time with your crypto bros on Telegram, but absolutely hate all of the garbage you get from non-verified world trades from influencers, which just keep losing money time after time. Well, I may have a solution for you today in the form of a Telegram bot. So if that sounds good to you, let's get straight to it. Hey, traders, I hope you're going extremely well. My name's David and welcome to my weekly segment on banter where I go through proven and profitable trading strategies.
**Trading Rules:**
- So if you're like me and absolutely love spending time with your crypto bros on Telegram, but absolutely hate all of the garbage you get from non-verified world trades from influencers, which just kee
- So if that sounds good to you, let's get straight to it.
- I really do feel as though if everybody's talking about it we should be able to code it and we should be able to trade it automatically.
**Strategy Components:**
- [trend] Whether it's a grid bot, whether it's a trend following bot, a sniper bot, there is really very little information.
**Context:** Timeframes: weekly, daily

---

## 11. This Buy/Sell Indicator is INSANE! (TradingView Indicator Test 2025)
*DaviddTech | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=2yH2nAC7G80

**Summary:** Today we're going to be looking at this indicator here and I'm going to be testing it as far as I possibly can to see whether or not it is possible. So if that sounds good, let's get straight to it. Hey traders, I hope you're all going extremely well. My name is David and welcome to my channel where I test trading indicators to see whether they are profitable on live markets. Okay, today we have a new indicator called the trend at speed analyzer by Xiaman himself.
**Trading Rules:**
- So if that sounds good, let's get straight to it.
- We're going to go up to indicators up the top here and then we're going to search for trend speed analyzer by Xiaman here has 3200 downloads when I started this video.
- Now we have a histogram down the bottom here, which allows us to tell whether we're looking for long positions when it goes green and short positions when it goes red.
- It does tend to have a dark red when the markets are moving faster.
- And when we're in more colon solidation periods, we have a light pink color here.
- And that tends to help us to stay out of market when markets are going sideways.
- We need to know exactly when we're going to get into our trades.
- So we'll be adding a couple of other indicators to keep us out of markets when markets are moving sideways.
**Strategy Components:**
- [trend] Okay, today we have a new indicator called the trend at speed analyzer by Xiaman himself.
- [trend] This is the trend speed analyzer by Xiaman.
- [trend] No matter whether the markets are ranging or actually trending.
- [momentum] And as you can see, it is a bit of an histogram down here at the bottom panel.
- [momentum] Now we have a histogram down the bottom here, which allows us to tell whether we're looking for long positions when it goes green and short positions when it goes red.
- [momentum] The histogram has gone green and the ADX has gone red over blue.
- [risk] Right, OK, for the stop loss and the take profit, we're going to use the trusty ATR bands.
- [risk] Now, the ATR bands by David Tech are a great way to set your stop loss and take profit as they adapt to market conditions and means you don't have exactly the same stop loss and take profit.
- [risk] So this helps you to get a better stop loss.
**Risk Management:**
- Stop below previous swing low.
**Entry/Exit Conditions:**
- Now we have a histogram down the bottom here, which allows us to tell whether we're looking for long positions when it goes green and short positions when it goes red.
- Right, OK, for the stop loss and the take profit, we're going to use the trusty ATR bands.
- Now, the ATR bands by David Tech are a great way to set your stop loss and take profit as they adapt to market conditions and means you don't have exactly the same stop loss and take profit.
- So this helps you to get a better stop loss.
- We're going to set the stop loss just like that.
- And then we're going to look for a risk to reward of one point five.
**Indicators:** for trend speed analyzer by Xiaman here has 3200 downloads when I started this vi, ATR, ADX

---

## 12. A Useful Chart for Navigating BTC Bear Market (Chart Shown: Year-To-Date ROI)
*IntoTheCryptoverse | asr_transcript | 2026-02-26*
Source: https://www.youtube.com/watch?v=rh5nqX3tUds

**Summary:** I think this is a really useful chart for navigating Bitcoin bear markets because it helps me to, you know, remain realistic about expectations rather than just race to Twitter to scream, you know, the super cycle or all season or or anything like that. Just look at the chart and see that this is exactly how people get sucked in and then end up losing a lot of their money in the midterm year because they try to chase a lot of these rallies that ultimately likely just end up resulting in lower highs that then lead us into lower lows as the year goes on.
**Raw Concepts:** I think this is a really useful chart for navigating Bitcoin bear markets because it helps me to, you know, remain realistic about expectations rather than just race to Twitter to scream, you know, the super cycle or all season or or anything like that. Just look at the chart and see that this is exactly how people get sucked in and then end up losing a lot of their money in the midterm year because they try to chase a lot of these rallies that ultimately likely just end up resulting in lower highs that then lead us into lower lows as the year goes on....

---

## 13. Claude AI can NOW Automatically Build and Improve Your TradingView Strategies (while you sleep)
*MichaelIonita | transcript | 2026-02-27*
Source: https://www.youtube.com/watch?v=77ikjQjdGFg

**Summary:** AI is now capable of improving your trading strategies while you're sleeping. Using the back testing engine that I've developed, AI can finally iterate through its own ideas and only give you a strategy if it's better than before. This is a gamecher and these are the results. I gave it the super trend strategy. It has rookie numbers as you can see.
**Trading Rules:**
- Using the back testing engine that I've developed, AI can finally iterate through its own ideas and only give you a strategy if it's better than before.
- And then I thought, what if it can create a better strategy than my botfast re-entry from the master class if I give it enough time?
- So, if you don't watch this video, you're missing out on a massive game changer in trading.
- And in about 10 minutes from now, if you continue watching this video, you will know everything you need to know to use this for yourself.
- And guys, make sure to like this video if it adds value to you because otherwise the YouTube algorithm will never know.
- I will put the link down below and choose your app Mac OS or Windows and when you open it up it will look something like this.
- And if you want to learn how to automate any Trading View strategy, especially the ones that you create with this AI, I will put a link to a video up top.
- I will still have to decide if I put it in Signnum or in my masterass.
**Strategy Components:**
- [trend] I gave it the super trend strategy.
- [trend] And this is how the Super Trend V4 strategy scores that I showed you in the beginning of the video.
- [trend] And I chose the super trend strategy as a demo because everyone has access to this, right?
- [risk] The AI was able to create a strategy that makes it into my top three riskreward ranking.
- [risk] I have my own riskreward score.
- [risk] And yes, shorting is risky, so it gets a lower score.
- [filter] And before I get a comment about overfitting or curve fitting, I know about this problem of course and I avoid it by testing on a lot of assets and then compiling a score.
**Entry/Exit Conditions:**
- And then I thought, what if it can create a better strategy than my botfast re-entry from the master class if I give it enough time?
- We want to make sure the mindset of the people joining is proper long-term, lower risk, higher portfolio value, right?
**Indicators:** of a better strategy than my Bfast re-entry
**Context:** Timeframes: weekly

---

## 14. Gold: Dubious Speculation
*IntoTheCryptoverse | transcript | 2026-02-27*
Source: https://www.youtube.com/watch?v=whCcobPN71w

**Summary:** Hey everyone, thanks for jumping back into the heavy metal verse. Today we're going to talk about gold dubious speculation. You can also use the coupon code ITC50 to get 50% off your first month of Into the Cryptoverse Premium. Let's go ahead and jump in. So, gold is back above 5200.
**Trading Rules:**
- Now, what's interesting is when you look at monthly candles for gold, I don't think you could look at this and be able to definitively say that the bull market has to be over, which has been the thesi
- Even if the top for silver is in, even in the case where silver has topped, gold could still go to an all-time high.
- Now, if silver has topped for the year, I do not I do not look at this chart and believe that it's like a top that will last for say 20 years.
- I would say for silver, if this is the top for the year, I might envision us sort of in in a top like this where we had in in 1974 where it might fall off for a while, but I would expect it to come ba
- And if you look at what silver did in 1973 or sorry 1974, you can see that it dropped about 43% and kind of consolidated with some lower highs for a while, but then eventually it built back up into an
- And when you look at gold or sorry when you look at silver in this move you can see that the correction that it just had was around 47%.
- Now one of the things we mentioned for silver is that it should get a counter trend rally that kind of tops out in the March April May time frame if history is any indication.
- If you look at at silver, if we overlay the price of silver with the price of gold, and we're just going to look back in history and kind of see how these two interact with each other.
**Strategy Components:**
- [trend] Now one of the things we mentioned for silver is that it should get a counter trend rally that kind of tops out in the March April May time frame if history is any indication.
- [trend] And I do sometimes wonder if if this is a trend line that's going to come into play as well, where, you know, you might see it bounce around here for a little while.
- [trend] And that's why I told you guys when silver was like 45% down, it didn't make sense to go panic sell it because usually you get a counter trend rally going into like the going into the spring, which is
- [risk] And back then, you know, it made a lot more sense to be underweight metals and overweight stocks and overweight riskier things like crypto.
**Context:** Timeframes: monthly | Assets: GOLD

---

## 15. Пазарът най-накрая удари таргетите ни около 70000$
*TradeTravelChill | asr_transcript | 2026-02-27*
Source: https://www.youtube.com/watch?v=pfBjvU0PQSc

**Summary:** And now, the market is at the end of the day and the targets we would have set up from a long time ago. The liquidation of every single bitcoin was more than 30,000, even a little bit. The cars are driving on Twitter in panic, and half of the retail is already out of the market. Most people at the moment are looking at the market and see that Haos is selling for a long time and are wondering why they didn't take this decision sooner. While some are panicking about the red candles, others are baking.
**Raw Concepts:** And now, the market is at the end of the day and the targets we would have set up from a long time ago. The liquidation of every single bitcoin was more than 30,000, even a little bit. The cars are driving on Twitter in panic, and half of the retail is already out of the market. Most people at the moment are looking at the market and see that Haos is selling for a long time and are wondering why they didn't take this decision sooner. While some are panicking about the red candles, others are baking....

---

## 16. How to trade like a pro (step by step) 🤖
*DaviddTech | transcript | 2026-02-27*
Source: https://www.youtube.com/watch?v=3pW6m2oTCDE

**Summary:** and retying the market prediction myth and replacing it with trading bots that actually work. I got consistent execution with minimal emotion interference. Most traders think success comes with accurate predictions. In reality, it comes from running a small edge repeatedly. So, to avoid this, number one, lock in your rules.
**Trading Rules:**
- So, to avoid this, number one, lock in your rules.
- Create at least three rules that cover your trading conditions, confirmations, and risk.
- If you're tired of being bottlenecked by your own trading, follow for more rules-based trading systems that run without your interference.
**Strategy Components:**
- [filter] So, to avoid this, number one, lock in your rules.
- [risk] Create at least three rules that cover your trading conditions, confirmations, and risk.
**Entry/Exit Conditions:**
- Create at least three rules that cover your trading conditions, confirmations, and risk.

---

## 17. "They're Down 50% Against Gold"
*IntoTheCryptoverse | transcript | 2026-02-28*
Source: https://www.youtube.com/watch?v=Tp7ENo2ii40

**Summary:** If you think, well, yeah, you've made a lot of money in stocks. I mean, like, I've done really well with just buying low expense ratio index funds for a long time, but it does not change the fact, and you guys know me. Like, I've always looked at opportunity costs. Like, think about altcoins and Bitcoin, how I spent four or five years, since 2022, early 2022 telling people that alts were bleeding to Bitcoin and there was no justification for for them as a long-term investment. The reality is how good stocks have been over the last few years since 2021.
**Trading Rules:**
- If you think, well, yeah, you've made a lot of money in stocks.
**Context:** Assets: GOLD

---

## 18. This Indicator Deleted Almost All of My False Signals!
*SoheilPKO | transcript | 2026-02-28*
Source: https://www.youtube.com/watch?v=ssu2qDoPyks

**Summary:** Listen, no matter what trading method you use or what trading strategy you use or what markets you're trading or what time frames you're trading, you always need to analyze volume. Taking a trading decision only based on the price is a blind decision. So volume analysis should be part of your trading strategy. In this video, I want to introduce three volume indicators that are excellent choices to use in your trading strategy. All right, let's add the first indicator.
**Trading Rules:**
- When it comes to a volume indicator, most of traders use a basic volume indicator like this one.
- This one which is an editor specs indicator and written by XDCO if I'm pronouncing it correctly.
- This one which is added here is just a simple volume indicator that you probably know if you have worked with this volume indicator.
- If the candle is closed green the color of the bar is green.
- And if the candle is closed red, the color of the bar is red.
- When we are using this volume indicator, we don't care about the colors.
- If we go to the settings of the indicator here in this part heat map threshold multipliers you can see that we have four different multipliers which are set at four 2.5 1 and minus.5.
- So for example when volume is at least four standard deviation above the average it is considered extra high and when it is one standard deviation above the average it is considered medium.
**Strategy Components:**
- [trend] Whether a breakout inside a trend or a breakout after a flat market.
**Indicators:** volume delta this one which is written by HAP harmonic

---

## 19. A trader’s nightmare: when an influencer can’t explain their edge…
*DaviddTech | transcript | 2026-02-28*
Source: https://www.youtube.com/watch?v=6Ex-hduaP9A

**Summary:** Sorry bro, you can't practice my strategy. So if two people look at exactly the same chart, are they going to take exactly the same trade? You just have to like feel the market. And your back test feels it too. So how do your students learn it or even understand it?
**Trading Rules:**
- So if two people look at exactly the same chart, are they going to take exactly the same trade?
- So, if you can't test it, verify it, or even explain it, why should I buy your course?

---

## 20. The Mechanism That Ends Business Cycles
*IntoTheCryptoverse | transcript | 2026-02-28*
Source: https://www.youtube.com/watch?v=bB6oo3oJc0k

**Summary:** Hey everyone and thanks for jumping back into the macroverse. Today we're going to talk about the mechanism that typically ends business cycles. Use the coupon code ITC50 to get 50% off your first month. Let's go ahead and jump in. So, we've been putting out videos for a while talking about how business cycles end.
**Trading Rules:**
- Late business cycle environments are characterized where higher risk assets bleed to lower risk assets.
- I've called it sort of rolling down the risk curve.
- That's when you have a contraction in the United States.
- When you do that, you get a chart that looks like this.
- When you look at it in this way and you see that each business cycle returns back down to these low levels, this metric does anyways, you can see that saying that hey there wasn't a recession in 2014.
- If you want to ignore the pandemic and say that we can't that was just sort of a black swan, you could argue that this business cycle has been going on since 2009.
- Okay, that's the equation and you can stop there if you want to.
- If you want to normalize it, which is what I like to do, you can divide all of it by the money supply M2.
**Strategy Components:**
- [risk] Late business cycle environments are characterized where higher risk assets bleed to lower risk assets.
- [risk] I've called it sort of rolling down the risk curve.
- [risk] And if you're curious why higher risk assets have been doing so poorly for so long, it's because we have been in a late business cycle environment for many years.
- [trend] So again even in the '90s the unemployment rate was trending higher.
**Entry/Exit Conditions:**
- Late business cycle environments are characterized where higher risk assets bleed to lower risk assets.
- I've called it sort of rolling down the risk curve.
- Okay, that's the equation and you can stop there if you want to.
- And if you're curious why higher risk assets have been doing so poorly for so long, it's because we have been in a late business cycle environment for many years.
**Context:** Assets: GOLD

---

## 21. Average day as an automated trader 🤖
*DaviddTech | transcript | 2026-03-01*
Source: https://www.youtube.com/watch?v=lGtVSCYaRZg

**Summary:** Okay, so being a trader who uses automation, my days vary quite a lot, one from another, but I guess that's part of the fun and kind of the point. Typically, my day starts before the whole of my house awakes. I barely sleep, and my brain has the habit of turning on early, whether I want it to or not. I make coffee and sit down quietly so I don't wake everybody else up. First thing I do is check my systems just to confirm everything is running the way it's supposed to.
**Trading Rules:**
- If something needs attention, I'll note it for a bit later.
- And if you want to see more trading content, make sure you hit.

---

## 22. Bitcoin: The Beauty of Mathematics (Part 68)
*IntoTheCryptoverse | transcript | 2026-03-01*
Source: https://www.youtube.com/watch?v=hAFvtCnrJAw

**Summary:** Hey everyone and thanks for jumping back into the cryptoverse. Today we're going to talk about Bitcoin, the beauty of mathematics part 68. You can also check out my other website benjenkowan.com as well. Let's go ahead and jump in. So the cryptocurrency market cap is coming in at around 2.29 trillion.
**Trading Rules:**
- And then when Bitcoin topped out, there was then no rotation into altcoins.
- And so, really, if you think about it, it all happens to align perfectly.
- Now, the hard part now is if we didn't go to durably overvalued, can we go the entire year without really starting to creep down to this lower regression trend line?
- So, there's still some room for the asset class to move down in the midterm year if it wants to.
- If you look at at Bitcoin, if we look at Bitcoin's total market cap, the market cap of Bitcoin is around 1.33 trillion.
- So with Bitcoin making up the difference, there's still more in Bitcoin than the altcoin market, but if Bitcoin continues to go down, which it likely will as the year goes on, it will drag the altcoin
- I'm not an expert on predicting when those counterturn rallies will occur.
- But I think the bare market still has some time to play out even if you do get a a counter trend rally, you know, potentially back up to the bull market support band or now bare market resistance band
**Strategy Components:**
- [trend] This is still about 50 to 55% I think 50 53.55% below that quote unquote fair value logarithmic aggression trend line.
- [trend] Now, the hard part now is if we didn't go to durably overvalued, can we go the entire year without really starting to creep down to this lower regression trend line?
- [trend] But I think the bare market still has some time to play out even if you do get a a counter trend rally, you know, potentially back up to the bull market support band or now bare market resistance band
- [risk] And then when everything else rolled over because we were in a late business cycle environment like 2019, you don't get that final rotation into higher risk assets because Bitcoin did not have its own
**Entry/Exit Conditions:**
- And then when everything else rolled over because we were in a late business cycle environment like 2019, you don't get that final rotation into higher risk assets because Bitcoin did not have its own
**Context:** Timeframes: daily

---

## 23. Трейдинг за начинаещи: Как трябва да изглежда денят ти !
*TradeTravelChill | asr_transcript | 2026-03-02*
Source: https://www.youtube.com/watch?v=5FkZrOoGmJc

**Summary:** If you start training today, in 2026, you will be able to do something different from 90% of the people. You will not be able to look for signals, you will not be able to jump between strategies. For sure, you will not be able to open your position and accept the principle. You will be able to build up a simple, repeatable day by day process. Because the truth is the following.
**Trading Rules:**
- If you start training today, in 2026, you will be able to do something different from 90% of the people.
- If you are starting, you want to do it seriously.
- If we are in the trend, what is the trend?
- Higher, higher, higher, higher high, higher high, higher high, higher high, higher high, and we enter the consolidation flag while we are still not doing it.
- When I look at it, I realize that we are down-trend.
- When I said this, I knew that the macro trend is not very good.
- If you took a similar trade, you can allow yourself to cover the AMA and the previous structure, namely this top hand here and then to drive this trend down.
- If you start trading seriously there is a little advantage and it matters.
**Strategy Components:**
- [trend] If we are in the trend, what is the trend?
- [trend] For example, the 7th graphic looks like a trend for us.
- [trend] The day graphic again looks like a trend for us.
**Entry/Exit Conditions:**
- So you have to know when we have lower days and lower levels in downtrend and when we have higher levels or consolidation in the next wave consolidation and in the next wave and after that Entry: the 
**Indicators:** for long-term long-term
**Context:** Timeframes: daily, 1m | Assets: BTC, GOLD, XRP

---

## 24. Bitcoin: The Early March Rally
*IntoTheCryptoverse | transcript | 2026-03-02*
Source: https://www.youtube.com/watch?v=R9yYJXpYYzg

**Summary:** Hey everyone and thanks for jumping back into the cryptoverse. Today we're going to talk about Bitcoin and we're going to be discussing this early March rally that we have been talking about for the last couple of weeks. Let's go ahead and jump in. So, one of the things that we have identified with Bitcoin in midterm years is that Bitcoin will often form a low in February and then it will tend to form a lower high in March. So, we're going to go through a few examples, but before we get to those examples, I want you to look at the average response of Bitcoin in midterm years around this time.
**Trading Rules:**
- So if you look at the year-to- date ROI of Bitcoin so far this year, this is what it looks like, right?
- Like if there is a rally and you hold nothing, then you're more likely to FOMO in and be that person that buys at the lower high.
- Whereas, if you just kind of have a small stack that you always hold no matter what, it kind of helps helps with that.
- Now, the only counterpoint to that is to say, what if the low here that we broke down from is more comparable to say the lows from from 2024?
- I don't know if it's going to let me move them over collectively, but what we're going to do is we're going to go look at at the next one.
- If you zoom in, technically it was late February, but again you did have renewed strength into early March and the top was March 5th.
- I don't remember when it was in 2014.
- When did the lower high occur?
**Strategy Components:**
- [trend] And that the main goal of midterm years is to not chase every single counter trend rally, but to preserve what you have because at the, you know, later on this year, a lot of these rallies no longer, 
- [filter] And what you'll notice is that back then what Bitcoin did was it it rallied for a week, got rejected, rallied again up to the bare market resistance band, even got a little bit above it, but ultimatel
- [filter] It went to the It went back up to the resistance band, got rejected, came back down.
- [filter] Like is there a chance that Bitcoin goes up to that gets rejected and then gets another rally into late March kind of like last cycle?
**Context:** Timeframes: daily

---

## 25. Using Crypto to Trade Gold & US Markets (Full Walkthrough)
*ECKrown | transcript | 2026-03-03*
Source: https://www.youtube.com/watch?v=XkdmG94fvqA

**Summary:** In this video, I want to show you how you can use your cryptos like your tethers, your USDC, your bitcoins, your salon, your ethereums, your uh camel coins, whatever to to put trades on other markets. When I say other markets, I'm talking about gold, silver, platinum, platium, all of the major US indices like SPY, NASDAQ, Dow Jones, and even other world markets as well, plus many, many more. all of the major US equities as well and even several different Forex pairs. That is going to be through Bybit, which is the link in the description below, which will give you several bonuses. But of course, full disclosure, it is an affiliate link, but I want to walk you through how you actually fund your account, how you put on trades, these sort of things.
**Trading Rules:**
- When I say other markets, I'm talking about gold, silver, platinum, platium, all of the major US indices like SPY, NASDAQ, Dow Jones, and even other world markets as well, plus many, many more.
- Honestly, if you're familiar with Bybit or any of the major crypto exchanges, you're already going to know how this works.
- She was trying to sign up to a Vanguard account to get uh, you know, access to the US markets when we were living in Europe.
- Uh but yeah if you're not US person it's probably the easiest way to get exposure to these major markets which you know are the ones that are typically moving.
- But of course, if you're just looking at Bitcoin, there's been [ __ ] all going on for the past month and for the couple months before that, you know, pretty much nothing going on over here as well.
- So, if you are a career trader or a career investor, you know, the opportunity cost is a real thing.
- But if you do want those bonuses, then yes, there is a nice benefit with that.
- I don't really know why you'd want to do that, but hey, if you do, it's all there for you.
**Strategy Components:**
- [risk] Of course, also on your order entry screen, if you can actually go through this, then you can also set up your takerit and your stop loss in advance.
- [risk] But at the very least, you can protect yourself and and manage risk that way.
- [confirmation] It also requires a trading volume as well.
**Risk Management:**
- Stop below previous swing low.
**Entry/Exit Conditions:**
- Of course, also on your order entry screen, if you can actually go through this, then you can also set up your takerit and your stop loss in advance.
- But at the very least, you can protect yourself and and manage risk that way.
**Context:** Assets: GOLD, NASDAQ

---
