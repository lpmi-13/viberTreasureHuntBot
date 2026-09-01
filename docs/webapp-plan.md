# Web scavenger hunt application plan

## 1. Goal and product principles

Replace the Viber conversation with a mobile-first progressive web app (PWA), while
preserving the useful core loop in the current application:

1. show a deliberately ambiguous photograph and useful local-language phrases;
2. have a student ask people nearby for directions;
3. verify the student's live location at the destination;
4. unlock the next clue; and
5. atomically declare the first valid finisher the winner.

The design should be inexpensive for a teacher or small school, require no app-store
installation, work for many participants in the same hunt, and avoid turning a hunt
into an internet-search exercise. “Search-resistant” cannot be guaranteed: image
search providers continually change, and a determined participant can photograph a
screen. The product should therefore combine clue-design feedback, light technical
deterrents, and teacher expectations rather than promise prevention.

## 2. User journeys

### Administrator / teacher

1. Sign in using a magic link or passkey.
2. Create a draft hunt with title, local language, start/end time, location and
   participant rules.
3. Add ordered stages. For each stage, upload a clue photo, write optional clue text,
   add direction-seeking phrases and place the answer pin on a map.
4. Choose an acceptance radius (default 75 m, with a warning below 30 m because phone
   GPS can be inaccurate) and optionally require a short answer or facilitator code.
5. Review automated and checklist-based image feedback, then crop, replace or approve
   the image with a recorded override reason.
6. Preview the exact participant experience, publish, and share a short join code/QR.
7. Watch a live dashboard showing joined, active, completed and withdrawn players;
   pause the hunt, extend its end time, disqualify obvious test/cheating accounts, or
   end it without selecting a winner.
8. Export a minimal CSV of results and delete the hunt and participant data.

### Participant / student

1. Open a URL or scan a QR code. Enter the hunt code and a teacher-visible display
   name; no account should be required by default.
2. Accept a concise safety/privacy notice and allow location only when checking in.
3. See the current photo, clue and a prominent “phrases to ask” panel. Do **not** show
   a map, coordinates, distance, compass bearing, EXIF data or progressively warmer
   hints unless the teacher explicitly enables them.
4. At the destination, tap **Check my location**. The browser obtains a fresh,
   high-accuracy reading and submits latitude, longitude, reported accuracy and time.
5. The server decides whether the accuracy circle plausibly intersects the configured
   radius. A success unlocks the next stage; a failure gives neutral encouragement,
   not a distance or direction that could replace conversation.
6. On the last successful check-in, see completion position and winner status. A live
   results view can reveal only what the teacher has configured.

Accessibility requirements include keyboard navigation, meaningful image alt text,
high contrast, large tap targets, screen-reader status announcements, and a teacher
controlled non-GPS fallback for students whose device or disability prevents location
use. Cache the current clue and phrase sheet for intermittent connectivity, but never
accept completion solely in the client.

## 3. Recommended architecture

### Recommended first version: Next.js PWA + Supabase

* **Web/UI:** TypeScript, Next.js and a responsive PWA deployed on Cloudflare Pages or
  Vercel. Use a small map component only in the admin UI. The participant UI uses the
  browser Geolocation API.
* **Managed backend:** Supabase Postgres, Auth, Storage and Realtime. PostGIS performs
  radius checks; row-level security separates administrators and participants;
  Realtime drives the admin dashboard.
* **Server logic:** server-side route handlers or Supabase Edge Functions implement
  joins, check-ins, publication, moderation and winner selection. Clients never write
  progress or winner fields directly.
* **Images:** private originals plus transformed participant renditions in object
  storage. Serve short-lived signed URLs and strip EXIF metadata during ingestion.
* **Monitoring:** structured event/error logs with no precise coordinates in routine
  application logs. Add an inexpensive hosted error tracker only when usage warrants.

This is the best balance for a small team: one relational source of truth, built-in
authentication/storage, spatial queries, transactions and an easy migration path.
Start on free tiers, but check current quotas and acceptable-use terms before every
real event; free-tier limits and sleep policies change.

### Logical component flow

```text
Participant/admin browser
        |
        v
Static/PWA host ---- server endpoints / edge functions
                           |
          +----------------+----------------+
          v                v                v
   Postgres/PostGIS   Object storage   optional image analysis
   + transactions     + signed URLs    worker/provider APIs
          |
          v
     realtime dashboard
```

Keep provider-specific code behind `AuthService`, `HuntRepository`, `ImageStore` and
`ImageAnalysisService` interfaces. This prevents the first cheap hosting choice from
becoming a permanent constraint.

## 4. Data model and concurrency

Use UUID primary keys, UTC timestamps and database constraints. Suggested tables:

| Table | Important fields |
| --- | --- |
| `profiles` | `user_id`, `display_name`, `role` |
| `hunts` | `owner_id`, `join_code_hash`, `status`, `starts_at`, `ends_at`, `winner_entry_id`, `language`, settings JSON |
| `hunt_admins` | `hunt_id`, `user_id`, `role` |
| `stages` | `hunt_id`, `position`, clue text, phrase set, answer geography/radius, image IDs |
| `entries` | `hunt_id`, anonymous session/user ID, display name, status, current stage, joined/completed timestamps |
| `check_ins` | `entry_id`, `stage_id`, submitted point, accuracy, result, server time, idempotency key |
| `image_assets` | private original key, safe rendition key, checksum, EXIF-stripped flag, analysis status/report |
| `audit_events` | actor, hunt, action, target and timestamp (never secrets or unneeded precise locations) |

Enforce one active entry per participant/hunt and unique `(hunt_id, position)` stages.
Join codes must be high entropy, rate limited and stored as hashes. Participant session
tokens are random, revocable and scoped to one entry.

### Correct winner selection

The final check-in endpoint must run one database transaction:

1. lock the entry and validate hunt status/time, expected stage and idempotency key;
2. perform the geospatial check on the server;
3. insert the accepted check-in and advance/complete the entry once;
4. set `hunts.winner_entry_id` only when it is null (a conditional update or row lock);
5. commit, then return the persisted winner.

This makes simultaneous finishes deterministic according to database commit order and
prevents duplicate taps or retries from producing multiple winners. Record all valid
finishers and their server timestamps so an administrator can audit/disqualify and,
if policy permits, promote the next eligible finisher. Document tie policy before the
hunt; do not compare device clocks.

## 5. Image difficulty and search-resistance feedback

Run analysis when an image is uploaded, asynchronously so authoring remains fast.
Return a report with evidence and suggestions, not a misleading “Google-proof” badge.

### Low-cost checks in the MVP

* strip EXIF, GPS, filename and camera metadata from the served rendition;
* OCR locally (for example, Tesseract/WASM or a small server worker) and highlight
  street names, business names, URLs, phone numbers, plaques and readable signs;
* estimate blur, contrast, resolution and feature density to identify unusably vague
  or trivially distinctive images;
* let the author mark obvious categories: full landmark/façade, unique artwork,
  transit stop, business branding, street sign or house number;
* generate a center/edge crop preview and recommend cropping/masking identifying text;
* compute a perceptual hash to catch reuse among images already stored by the school;
* require preview confirmation: “Could a student identify this without asking a
  person?” and “Does it contain searchable words or a famous landmark?”

Suggested outcomes are **likely too easy**, **review recommended**, and **no obvious
issues found**. The last outcome explicitly does not mean search-proof.

### Optional paid/experimental checks

* cloud vision OCR and landmark/logo/web-entity detection generally improve recall;
* a licensed reverse-image-search API can test exact or visually similar public
  matches, subject to provider terms, cost and coverage;
* an image-capable model can explain distinctive/searchable elements, but its answer
  is advisory and images must not be sent to a third party without an appropriate
  privacy agreement.

Do not scrape consumer Google Images or automate uploads against its terms. There is
no dependable public test proving that an image cannot be found later. For especially
sensitive hunts, use teacher-taken detail shots, avoid famous landmarks and public web
images, crop identifiable text, rotate clue sets, reveal each clue only after start,
and have staff pilot every hunt with ordinary image and text searches.

Technical deterrents such as signed URLs, `noindex`, disabled social metadata and
watermarked/per-participant renditions reduce accidental sharing/indexing but cannot
stop screenshots. Watermarks should avoid covering the visual clue and should not
contain the hunt/location name.

## 6. Security, privacy, safety and anti-cheating

* Use TLS, secure/HTTP-only/same-site cookies, CSRF protection, strict content security
  policy, upload MIME sniffing, size limits and image re-encoding. Never trust EXIF or
  client coordinates as authoritative evidence.
* Authorize every operation at the database and endpoint layers. Admin routes require
  authentication and ownership; participant tokens can access only their current
  clue and their own coarse progress.
* Apply per-IP, per-entry and per-hunt rate limits to joins and check-ins. Reject stale
  readings and implausibly poor accuracy; flag impossible travel speed and repeated
  identical coordinates for teacher review rather than automatically accusing a
  student.
* Browser geolocation can be spoofed. Higher-assurance options are rotating QR codes
  displayed by a person/business at each destination, a staff PIN, or facilitator
  approval. These preserve the language interaction better than invasive tracking.
* Collect location only on a check-in tap, round or delete failed coordinates quickly,
  and retain successful points only as long as the teacher needs results. Publish a
  retention schedule and one-click deletion. Avoid ad trackers.
* Assume some participants are minors: obtain the school's privacy/safeguarding review,
  minimize names and precise location, avoid public leaderboards by default, provide
  emergency/contact instructions, mark safe boundaries, and never direct students
  onto private property or unsafe roads. Verify applicable local law and school policy.

## 7. Hosting and service options

Pricing changes frequently, so these are architectural comparisons rather than price
quotes. Validate current pricing, quotas, egress, data residency, backups and support
before launch.

| Option | Components | Cost/operations profile | Trade-offs |
| --- | --- | --- | --- |
| **Supabase + Cloudflare Pages/Vercel (recommended)** | Managed Postgres/PostGIS, Auth, Storage, Realtime; hosted Next.js/PWA | Often free for a prototype and low monthly cost for a small production hunt | Fastest relational implementation; watch inactive-project, storage, egress and realtime limits; two vendors |
| **All Cloudflare** | Pages/Workers, D1, R2, Durable Objects, Turnstile; external auth or Access | Very low request/storage/egress costs and global edge execution | More custom auth and data logic; D1 geospatial/concurrency design is less convenient than Postgres; Durable Objects fit per-hunt serialization |
| **Firebase** | Hosting/App Hosting, Auth, Firestore, Storage, Cloud Functions | Generous prototype experience; usage-based operations can be economical at small scale | Winner transactions are feasible, but relational reporting and radius queries need denormalization/geohashes; billing surprises require budgets/alerts |
| **Google Cloud managed** | Cloud Run, Cloud SQL/Postgres, Identity Platform, Cloud Storage | Scales cleanly; can use Vision APIs in the same platform | Cloud SQL baseline and operational complexity usually cost more than the recommended MVP |
| **AWS managed/serverless** | Amplify/CloudFront, Cognito, Lambda, API Gateway, DynamoDB or Aurora, S3 | Broadest service choice and strong scaling | More configuration and cost dimensions; DynamoDB needs careful conditional-write/index design; Aurora has a higher baseline |
| **Single small VPS** | Dockerized web app, Postgres/PostGIS, object storage/files, reverse proxy | Lowest predictable cash cost at steady small usage | Teacher/operator owns patching, backups, monitoring, email delivery, failover and security; not recommended for minors' location data without expertise |
| **Portable PaaS** | Render, Railway, Fly.io or similar plus managed Postgres/object storage | Simple deployment and moderate predictable spend | Free offerings and sleep/egress policies change; confirm region, backup and scaling behavior |

Authentication choices, from least participant friction to most control:

* **Recommended:** managed magic-link/passkey auth for administrators; scoped anonymous
  participant sessions created from a join code. This avoids collecting student email.
* Managed auth for everyone (Supabase Auth, Firebase Auth, Auth0, Clerk, Cognito) is
  useful where the school needs identity, SSO or audit support, but may add per-active-
  user charges and personal data.
* School OIDC/SAML provides lifecycle control but is commonly a paid enterprise feature
  and takes coordination with school IT.
* Self-hosted auth saves license fees only at sufficient scale; it increases security,
  email deliverability and recovery responsibility and is not an MVP cost saving.

For cost control, resize images at ingestion, cap uploads and retention, avoid polling,
set provider budgets/alerts, load-test with the expected class count plus margin, and
maintain an export/restore drill. Do not rely on a sleeping free database immediately
before a scheduled event; warm and rehearse the production hunt.

## 8. Delivery plan

### Phase 0 — discovery and prototype (about 1 week)

* confirm class size, countries/data rules, devices, connectivity, languages and tie
  policy;
* prototype geolocation accuracy at several intended sites and test the language-first
  failure feedback with students;
* choose provider/region and write retention, consent and safeguarding requirements.

**Exit:** a phone can obtain acceptable readings at representative destinations, and
the school approves the data/safety model.

### Phase 1 — playable vertical slice (about 2 weeks)

* PWA shell, admin authentication, hunt/stage CRUD, upload/re-encode/EXIF stripping;
* anonymous join, current clue/phrases, server-side check-in and sequential progress;
* transactional first-winner selection and basic results page;
* automated tests for authorization, radius boundaries, retries and concurrent finish.

**Exit:** two browsers can join the same private hunt, progress independently and
produce exactly one winner under a concurrency test.

### Phase 2 — safe pilot (about 1–2 weeks)

* OCR and author checklist/report, crop/mask flow, admin preview and publish validation;
* live dashboard, pause/end/disqualify/audit functions and CSV export;
* rate limits, deletion/retention job, accessibility pass, offline clue cache, error
  monitoring and backup/restore exercise.

**Exit:** a staff-only field test succeeds under weak connectivity, and threat/privacy/
safeguarding reviews have no unresolved high-risk finding.

### Phase 3 — optional enhancements

* paid landmark/logo/web-match analysis behind a per-hunt budget;
* rotating on-site QR/PIN verification, team entries, school SSO, hunt templates,
  translations and richer post-hunt analytics;
* provider abstraction/migration only when actual usage or compliance justifies it.

## 9. Test strategy and launch checklist

Automate unit tests for geospatial boundaries, progression and image-report rules;
integration tests for row-level security, signed image access and retention deletion;
and browser tests for admin authoring and participant completion. Include a parallel
test that submits many final check-ins and asserts one winner, plus duplicate/reordered
request tests. Security-test cross-hunt access, guessed join codes, malicious uploads,
stored XSS, IDOR and rate limiting.

Before each live hunt:

* walk the route, confirm every pin/radius and assess physical accessibility/safety;
* pilot every image with OCR, ordinary text/image search and a person unfamiliar with
  the route;
* publish a cloned practice hunt, warm the services and simulate expected concurrency;
* verify a backup/export, admin recovery, support contact and manual check-in fallback;
* confirm start/end timezone, winner/tie/disqualification rules and leaderboard privacy;
* after the event, export only needed results and run the promised deletion schedule.

## 10. Key decisions to confirm before implementation

1. Maximum simultaneous participants and typical number/size of clue images.
2. Individual versus team play, and whether a teacher may revise the winner.
3. Countries, participant ages, required data residency and school identity provider.
4. Expected connectivity and whether on-site QR/PIN fallback is practical.
5. Desired retention period and whether precise successful locations are needed after
   validation at all.
6. Monthly/event budget and willingness to pay for third-party vision/search checks.
7. Whether clue order is fixed, randomized per participant or supports branching.

Unless these answers require otherwise, build the Supabase-backed vertical slice,
keep participants anonymous, store minimal location data, and treat image feedback as
an author-assistance tool rather than an anti-cheating guarantee.
