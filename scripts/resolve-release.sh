#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GH_REPO:?GH_REPO is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
: "${GITHUB_STEP_SUMMARY:?GITHUB_STEP_SUMMARY is required}"

if [[ -n "${REQUESTED_TAG:-}" ]]; then
  tag="$REQUESTED_TAG"
  [[ "$tag" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Invalid release tag" >&2; exit 1; }
  tag="$(gh api "repos/wiserain/rclone/releases/tags/$tag" --jq '.tag_name')"
else
  tag="$(gh api repos/wiserain/rclone/releases/latest --jq '.tag_name')"
fi
[[ "$tag" =~ ^[A-Za-z0-9._-]+$ ]] || { echo 'Invalid release tag' >&2; exit 1; }

ref_json="$(gh api "repos/wiserain/rclone/git/ref/tags/$tag")"
kind="$(jq -r '.object.type' <<< "$ref_json")"
sha="$(jq -r '.object.sha' <<< "$ref_json")"
for _ in {1..6}; do
  [[ "$kind" != tag ]] && break
  annotated="$(gh api "repos/wiserain/rclone/git/tags/$sha")"
  kind="$(jq -r '.object.type' <<< "$annotated")"
  sha="$(jq -r '.object.sha' <<< "$annotated")"
done
if [[ "$kind" != commit || ! "$sha" =~ ^[a-f0-9]{40}$ ]]; then
  echo "Failed to resolve Git commit for release $tag" >&2
  exit 1
fi

build=true
if [[ "${FORCE_BUILD:-false}" != true ]] && gh release view "aar-$tag" --repo "$GH_REPO" >/dev/null 2>&1; then
  build=false
fi

{
  printf 'tag=%s\n' "$tag"
  printf 'sha=%s\n' "$sha"
  printf 'build=%s\n' "$build"
} >> "$GITHUB_OUTPUT"
{
  echo '## Upstream release'
  echo "- Tag: $tag"
  echo "- Commit: $sha"
  echo "- Build required: $build"
} >> "$GITHUB_STEP_SUMMARY"
