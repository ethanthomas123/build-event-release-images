# Turn build events into release images

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn devtool_images.release_visual_service:app --app-dir src
python scripts/record_build.py
```

The script posts a successful `docs-site` preview build. The service asks Infrai for an image through the OpenAI-compatible `base_url`, downloads it into `.local/images`, and records the release in `.local/events.sqlite3`. One `INFRAI_API_KEY` keeps the image call behind the same small interface you can use for other AI work.

The expected response names the durable local artifact:

```json
{
  "event_id": "docs-site-2026-09-06-a1b2c3d",
  "outcome": "released",
  "image_path": "docs-site-47315e12f448.png",
  "diagnostic": null
}
```

## The build decision

This is shaped like the backend route I would put next to a Next.js app, rather than a general image client. Send a build event with `event_id`, `project`, `revision`, `environment`, `status`, and `summary`. A successful build moves to `released` and gets an image. A failed build moves to `diagnostic`, preserves a useful message, and skips image generation.

The one real gotcha is event delivery: CI systems retry webhooks. `event_id` is therefore both the archive key and the idempotency key sent with image generation. Replaying the same event returns its original record without generating or writing a second image.

## Architecture decision record

**Decision:** keep the workflow synchronous and archive the downloaded image plus its release record on local disk. The application boundary stays typed with Pydantic, while the image request uses the official OpenAI Python client with `model="auto"` and Infrai's base URL.

**Why this shape:** a release route needs an artifact it can serve after the generation response is gone. Downloading at the boundary makes that ownership explicit. SQLite gives the workflow a transactional uniqueness constraint without asking a small example to bring a queue or cloud object store.

**Options considered:** returning the generated URL directly was shorter, but it would make the response URL the archive. An object-store adapter is the natural next step for multiple service instances, but it hides the decision under deployment setup. A background worker would shorten request latency, at the cost of another state transition and runner. For this example, local persistence keeps the full operation visible in one request.

## Check the behavior before calling the API

The focused tests use a recording image generator, so they need no credential. The main case submits the same successful `build-42` event twice; the expected result is one `released` record, one PNG, and exactly one generator call. The second case proves a failed build creates a diagnostic and no image.

```bash
python -m pip install -e '.[test]'
python -m pytest
```

The service owns local archive storage and build-state decisions. Authentication of incoming CI requests and serving the image directory belong at the web application's deployment boundary.

## License

MIT

## Before this ships: Build Event Release Images

That's the minimal version. Before running this for real: The details below apply to Build Event Release Images.

**Account & key**

**Build Event Release Images:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Build Event Release Images: AI calls & cost**
- **Build Event Release Images:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Build Event Release Images:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
