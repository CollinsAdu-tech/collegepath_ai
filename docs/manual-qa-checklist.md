# Manual UI QA Checklist (Phase 11)

Everything below was verified programmatically (full-stack curl tests,
137 automated backend tests) except what genuinely requires a human
clicking in a real browser — that's what this checklist covers. Run
`npm run dev` (frontend) and `uvicorn app.main:app --reload` (backend)
together, open http://localhost:5173, and go through this list.

## First load / empty state (Section 28)
- [ ] Headline, subtitle, category chips, and suggested questions all render
- [ ] Header shows "Online" (green dot) within a second or two of load
- [ ] Stop the backend, reload the page: header should show "Offline"

## Category chips (Section 31)
- [ ] Clicking a category filters the suggested-questions list to that topic
- [ ] Clicking the same active category again clears the filter (shows all)
- [ ] Chips scroll horizontally on a narrow window rather than wrapping awkwardly

## Sending a message (Section 27, 34)
- [ ] Typing and pressing Enter sends; Shift+Enter inserts a newline instead
- [ ] Clicking a suggested question sends it immediately
- [ ] The send button is disabled while a request is in flight
- [ ] Rapidly pressing Enter multiple times sends only ONE message, not several
- [ ] Typing indicator (three dots) appears while waiting, disappears on response

## Confident answer (Section 29, 32, 33)
- [ ] Answer card shows: teal accent, category pill, answer text
- [ ] Source line shows a real clickable link with a verification date
- [ ] "You may also want to ask" shows 1-3 questions
- [ ] Clicking a related question sends it as a new message and gets an answer
      (not a fallback — this was a real bug found and fixed in Phase 10)
- [ ] Thumbs up/down buttons toggle to "Thanks for the feedback."

## Fallback answer (Section 18, 32)
- [ ] Ask something off-topic (e.g. "what's the weather") — card shows brick
      accent, the "not confident" message, and "Try one of these instead"
      with clickable suggestions
- [ ] Clicking one of those suggestions gets a real answer

## Dynamic / current-info answer (Section 24)
- [ ] Ask "What is Harvard's current application deadline?" — answer never
      states a specific date, shows an amber "may change by cycle" badge,
      and the source line says to check the college's page directly
      (no dead link)

## Error state (Section 35)
- [ ] Stop the backend mid-session, send a message — shows the
      "couldn't connect" message in a distinct (brick) card, not a crash

## Accessibility (Section 36)
- [ ] Tab through the whole page — every interactive element gets a visible
      focus ring
- [ ] Category chips and related-question buttons are reachable and
      activatable via keyboard (Tab + Enter/Space)
- [ ] Zoom to 200% / narrow the window to ~360px — layout stays usable,
      no horizontal scroll on the page itself

## Responsive (Section 27, 55)
- [ ] Resize from desktop width down to a phone-sized viewport — header,
      hero, chat bubbles, and input all remain readable and usable
