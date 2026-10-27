# Release migration

This standalone source repository is prepared for private review. **Publishing still belongs to [the original monorepo workflow](https://github.com/geonodecom/scraper-api-sdks/blob/main/.github/workflows/make-com-publish.yml).** No workflow, credential, registry ownership, or platform deployment has been migrated here.

Repository metadata now points to `geonodecom/integration-make` where supported. Existing published artifacts keep their old source metadata until an approved release. Package and platform identifiers are unchanged.

Before moving publishing:

1. Review the extracted history and license; confirm the private repository is the intended source of truth.
2. Run local checks and a controlled live workflow against a test account. Check authentication, errors, polling and relevant webhooks.
3. Update the existing release workflow for root-level paths and confirm the approved version/changelog. Coordinate with the original workflow so only one repository can release.
4. Configure the new repository's release identity and environment through the platform's own controls. Do not copy credentials into source files.
5. Validate the built artifact and its source/docs links; publish only as a separate approved release. Verify installation and a real workflow after release.

## Identity to preserve

- Template metadata name: `scraper-api`; major app version: `1`; `private: true`.
- Existing deployed app: `scraper-api-production`, zone `https://us2.make.com`. Existing CI overrides template defaults with `MAKE_APP_NAME` / `MAKE_ZONE_URL` and uses the appropriate team ID. Confirm those settings with the platform administrator before a release.
- Keep connection and module identifiers unchanged. Do not create a duplicate app.
- Existing CI uses a Make API token. Its credentials and scopes require an explicit handover; this source repository has no deploy token.
- There is no public marketplace listing. Access remains by request.

## Signup offer release check

The README uses the product-owner-approved launch copy, “Sign up to get 10,000 free credits” (21 October 2026). Before public release, verify that the live signup flow and account credit allocation match this offer. This copy update does not configure billing or issue credits.

## Cross-link deployment handoff

The README and package homepage link to the live [integrations hub](https://geonode.com/integrations). The intended detail destination is `https://geonode.com/integrations/make`; it is a deployment target, not a verified public page. After that detail page is deployed and checked, replace the hub fallback in README/package metadata with the detail URL and retain an API documentation link.

Source metadata targets `https://github.com/geonodecom/integration-make`; the repository remains private until its separate release decision. These local metadata edits do not alter an existing PyPI/npm listing. Carry them into the authoritative publishing source at the coordinated next release, then verify the registry's rendered README, source/issue links and homepage. Keep existing package names, versions and import identifiers unchanged during preparation.
