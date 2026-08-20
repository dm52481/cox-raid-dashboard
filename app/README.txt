CoX Live Raid Dashboard v11

Configured log:
C:\Users\Doonie\.runelite\raid-data tracker\cox\raid_tracker_data.log

Open:
http://127.0.0.1:8081

Stats changes
-------------
- New Stats layout replaces the old duplicate Existing Stats snapshot.
- Purple luck now includes the point totals used for the expectation calculation.
- Rolling Performance has tabs for Any size and team sizes 1 through 5.
- Purple History is now a compact sortable-style history table layout rather than horizontal cards.
- Special loot graphics use OSRS Wiki MediaWiki file redirects when the browser can reach the wiki.
  If an image cannot be loaded, the dashboard remains fully usable and shows the item text.
- Purple distribution and the main Special Loot column also display item icons.

Stats period selector:
All Time | Last 30 Days | Last 3 Months | Last 6 Months | Last 50 Raids | Last 100 Raids

Purple definition
-----------------
Purple means a CoX unique drop. Twisted ancestral colour kit and Metamorphic Dust are
special loot, but are excluded from purple luck and dry-streak calculations.


v12 — Valuable Drops screenshots
--------------------------------
Purple History can now show a RuneLite screenshot for personal purple drops.

Screenshot discovery:
1. The server looks at solo special-loot records and uses the receiver name to
   infer the RuneLite <account> folder.
2. It first searches:
      .runelite\<account>\screenshots\Valuable Drops
3. If that account cannot be matched, or a screenshot is not found there, it
   searches every discovered Valuable Drops folder under .runelite.

Screenshot association:
- Personal purple drops only.
- Uses RuneLite screenshot timestamps (for example YYYY-MM-DD_HH-MM-SS) and
  matches the closest screenshot to the raid log timestamp.
- File modification time is used as a fallback if a filename timestamp cannot
  be parsed.
- A screenshot must be within 10 minutes of the raid timestamp.
- Each screenshot can only be matched to one purple.

Viewing:
- Purple History has a Screenshot column.
- Click View to open the local screenshot in a dashboard overlay.
- The server only permits image files underneath the local .runelite folder.


v13 screenshot diagnostics/fixes
--------------------------------
- Removed Python invalid-escape SyntaxWarnings from screenshot docstrings.
- The inferred account from the supplied raid-log pattern should be YaDoons.
- Valuable Drops discovery now recursively searches all of .runelite.
- Valuable Drops subfolders are scanned recursively for image files.
- Screenshot filename timestamp parsing supports more RuneLite-style formats.
- Matching first tries 15 minutes, then uses a 2-hour fallback if necessary.
- Dashboard header now shows diagnostics such as:
    account YaDoons · 1 folder · 25 images · 4/5 personal purples matched
  This makes it obvious whether discovery or timestamp association is failing.


v14 — Boss Kills screenshots
----------------------------
Screenshot matching now uses:
    .runelite\<account>\screenshots\Boss Kills

Matching is verified using metadata embedded in the screenshot filename:
- CoX / Chambers of Xeric raid type
- KC number
- Calendar date
- Timestamp proximity when available

The matcher strongly prefers:
1. inferred account folder from a solo personal special-loot receiver;
2. exact KC + date;
3. exact KC + CoX filename identification;
4. date + CoX + close timestamp.

If no match exists in the inferred account folder, all Boss Kills folders under
.runelite are searched.

Purple History still provides a View button for matched personal purples.


v15 — portable first-run configuration
--------------------------------------
- Defaults to C:\Users\<current Windows user>\.runelite.
- If missing, the dashboard prompts with a native folder picker.
- First launch requires selection of a discovered RuneLite account.
- Change .runelite Folder and Change Account buttons are available in the dashboard.
- Selection persists in dashboard_config.json.
- Raid log lookup prefers the selected account, then supports the older shared raid-data tracker layout.
- Boss Kills screenshots are scoped to the selected account first.


v16 — account dropdown fix
--------------------------
RuneLite account choices are now populated from:
    .runelite\screenshots\<account>

The immediate folder names under .runelite\screenshots appear in an Account
dropdown directly in the dashboard.

- One account: selected automatically.
- Multiple accounts: choose one from the dropdown.
- Changing the dropdown saves the account and reloads screenshot matching.
- No file explorer is used for account selection.
- The folder picker is only for choosing .runelite itself.
- Boss Kills screenshots are read from:
    .runelite\screenshots\<selected account>\Boss Kills


v17 — Rolling Performance mode tabs
-----------------------------------
Rolling Performance now has two filter rows:

Mode:
    All | CM | Regular

Team size:
    Any size | 1 | 2 | 3 | 4 | 5

The two selections are combined before calculating Last 10 / 25 / 50 raid
performance.


v18 — automatic screenshot account selection
--------------------------------------------
On first launch, if multiple folders exist under:

    .runelite\screenshots\<account>

the dashboard scores each account's Boss Kills screenshots against the raid log.

Matching uses the same strong verification signals as Purple History:
- CoX / Chambers of Xeric identification
- KC number
- calendar date
- timestamp proximity when available

The account with the highest number of verified matches is automatically saved
as the default screenshot account.

If no account produces any verified matches:
- one available account is selected automatically;
- multiple accounts remain available in the dashboard dropdown for manual choice.

The Account dropdown can always be used to override the automatic selection.


v19 — global Stats mode selector
--------------------------------
All | CM | Regular is now at the top of the Stats section.

The selected mode applies to every Stats box/table beneath it, including:
- Purple luck
- Current personal dry streak
- Longest points dry streak
- Team-size performance
- Rolling performance
- Purple distribution
- Purple history
- Special loot by player

The mode selector combines with:
- the Stats time-period selector; and
- Rolling Performance's Any size / 1 / 2 / 3 / 4 / 5 selector.

Rolling Performance no longer has its own All / CM / Regular row.


v20 — Personal points per hour
------------------------------
Per-raid personal points/hour:
    personalPoints / (raidTimeSeconds / 3600)

Aggregate points/hour uses total personal points divided by total raid time,
which correctly weights raids by duration.

Added to the top summary, Team-size performance, Rolling performance, and CSV.


v21 — browser lifetime / automatic shutdown
-------------------------------------------
- Each dashboard browser tab gets a unique local session ID.
- Tabs heartbeat the local server every 8 seconds.
- Sessions expire after 30 seconds without a heartbeat.
- The process exits once all previously active tabs have expired.
- There is a 60-second startup grace period in case the browser fails to open.
- Multiple dashboard tabs are supported; closing one does not stop the app while
  another active tab remains.
- Refresh/navigation does not immediately unregister a tab, avoiding accidental
  shutdowns during normal page reloads.
- A Quit Dashboard button immediately requests server shutdown.


v22 — presentation/statistics redesign
--------------------------------------
Top summary:
- Raids
- Purples / Kits / Dust
- Total Loot Value

Main table:
- optional Personal pts/hr via Columns

Performance:
- Personal Bests
- Team-size Performance includes Avg Personal %

Purple Tracking:
- Purple Luck shows actual vs expected and ahead/behind
- Purple History includes Dry Before Drop
- personal drops receive a YOUR DROP badge

Stats are grouped into Performance, Purple Tracking, and Loot.


v23 — Death data hidden
-----------------------
The deaths field is not displayed anywhere in the dashboard and is excluded
from CSV exports because the source log value is known to be unreliable.


v24 — compact summary and flexible Stats periods
------------------------------------------------
- Receiver name is badge-styled for personal purples in Purple History.
- Removed Highest Personal % from Personal Bests.
- Stats periods: All Time, 1/3/6/12 Months, Custom Time Interval,
  Custom Number of Raids.
- Top summary cards no longer stretch to fill the full page width.
- Purple/Kit/Dust values carry their category colors; headers are neutral.


v25 — Team-size Performance update
----------------------------------
- Added Avg Overall Pts.
- Purple +/- now shows:
      actual purples - (overall points / 860,000)
  instead of a raid-percentage purple rate.


v26 — Regular Loot grid
-----------------------
Added a RuneLite-style Regular Loot grid to Stats -> Loot.

The grid aggregates quantities and values from lootList for the current Stats
selection and sorts items by aggregate GP value. It uses OSRS Wiki icons and
shows quantity, item name, and hover details.


v27 — Loot layout
-----------------
- Special Loot by Player and Regular Loot prefer a side-by-side layout.
- Regular Loot is limited to a maximum of five columns.
- Regular-loot cells/icons are smaller.
- Layout stacks on narrower windows.


v28 — historical Purple Distribution weighting
----------------------------------------------
Purple Distribution now shows Received, Expected, and +/-.

Weighting rules:
- before 2026-08-12: old table, total 69
- on/after 2026-08-12 Regular: new Regular table, total 60
- on/after 2026-08-12 CM: new CM table, total 56

Expected is accumulated one observed purple at a time based on that raid's
date and mode.


v29 — compact loot presentation
-------------------------------
- Added item icons to Purple Distribution.
- Regular Loot cells reduced to roughly half-height.
- Regular Loot item-name text removed; tooltip remains.
- Maximum Regular Loot width remains five columns.


v30 — Purple Distribution receiver filters
------------------------------------------
Added All receivers plus one filter per receiver to Purple Distribution.
Received, Expected, and +/- recalculate for the selected receiver only.


v31 — Purple Distribution receiver dropdown
-------------------------------------------
Replaced per-receiver filter buttons with a single Receiver dropdown.


v32 — control layout
--------------------
- Refresh Now moved beside the LIVE status indicator.
- Columns moved to the right edge above the raid table.
- Added a down-chevron to the Columns button.


v33 — summary/table/loot update
-------------------------------
- Showing # of # raids moved left of Columns.
- Top loot values: Purple / Regular / Total.
- Loot grid now includes purple uniques plus regular loot.
- Kits and dust remain excluded.


v34 — loot-value placement
--------------------------
- Top summary restored to Total Loot Value only.
- Purple / Regular / Total values moved to the top of the Loot grid.
