from whitenoise.storage import CompressedManifestStaticFilesStorage


def _without_source_maps(patterns):
    """Drop the sourceMappingURL rules from Django's hashed-files patterns."""
    cleaned = []
    for extension, rules in patterns:
        kept = tuple(rule for rule in rules if "sourceMappingURL" not in (rule if isinstance(rule, str) else rule[0]))
        cleaned.append((extension, kept))
    return tuple(cleaned)


class ManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Hashed + compressed static files that tolerate vendored libraries' source-map comments.

    Vendored Bootstrap ends with `/*# sourceMappingURL=bootstrap.min.css.map */` and the `.map` file is
    deliberately not shipped (it only helps an open DevTools). Django's hashing storage treats a reference to
    a missing file as fatal, which would fail `collectstatic` at image build time. Dropping that rule leaves
    the vendored file byte-identical, so the checksum recorded in static/vendor/README.md stays checkable.
    """

    patterns = _without_source_maps(CompressedManifestStaticFilesStorage.patterns)
