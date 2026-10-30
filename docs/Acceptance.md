# How you know a change is done

**"Done" cannot be a matter of opinion when four people are deciding it
separately.** Every box below is something you can check in a minute, without
asking anybody.

## Every pull request

- [ ] `python -m unittest` passes, and so does the `test` check.
- [ ] `python tools/no_leak.py` passes, and so does the `no-leak` check.
- [ ] **The app was run and the changed screen was looked at**, not only tested.
- [ ] Every colour comes from a token in `src/static/style.css`. No new hex in
      a template.
- [ ] No comment, no docstring, no em dash. Canadian English in anything a
      person reads.
- [ ] No label, keyword list or supplier detail is quoted in the description
      or a comment.
- [ ] The pull request does one thing and says which track it belongs to.

## The source

- [ ] Refresh loads the listings on the saved pages in `fixtures/`.
- [ ] Refresh twice in a row: the second one finds nothing new.
- [ ] The code holds no address of the live CIVD site, and no test opens a
      network connection.
- [ ] A listing whose attachment id changes keeps its card, and All Tenders
      marks it Updated.

## The filter

- [ ] A listing whose title holds a keyword lands in Bidding, Spotted.
- [ ] A listing with no keyword lands in All Tenders, and a search finds it.
- [ ] A listing sent to Bidding stays in All Tenders, shaded and tagged with its
      stage, with Open card in place of Send to Bidding.
- [ ] Emptying the keyword list shows everything rather than nothing.

## The model

- [ ] With the mode Off, a refresh never contacts a model.
- [ ] With the model unreachable (no key, no network, or Ollama stopped), a
      refresh finishes and moves nothing on the model's account.
- [ ] A keyword match is never sent to the model.
- [ ] The model never sees an attachment id.
- [ ] A card the model sent shows the model's reason in a dashed box, on the
      board and on the card. A keyword match shows none.

## The board

- [ ] Dragging a card to another column keeps it there after a reload.
- [ ] Moving a card into Submitted adds its title's words to the keyword list,
      shown with a dashed outline in Settings.
- [ ] Dismiss greys a card in place; the next day it is in Dismissed, and
      Restore brings it back.
- [ ] The reminders bell lists every key date in the next week on open cards in
      Bidding and Fulfillment, and nothing from All Tenders, Lost or Cancelled.
- [ ] A listing leaves All Tenders 30 days after it closes, a search still finds
      it, and one never sent to Bidding is deleted 60 days after it closes.
