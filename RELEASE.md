# Steps to release a new version

## Preparing for the release

- Check out a branch named for the version: `git checkout -b release-1.1.1`
- Change version in setup.py and stackermods/\_\_init\_\_.py
- Update CHANGELOG.md with changes made since last release (see below for helpful
  command)
- add changed files: `git add setup.py stackermods/\_\_init\_\_.py CHANGELOG.md`
- Commit changes: `git commit -m "Release 1.1.1"`
- Create tag: `git tag -am "Release 1.1.1" 1.1.1`
- Push branch up to git: `git push -u origin release-1.1.1`
- Push tag: `git push --tags`
- Open a PR for the release, ensure that tests pass

## Releasing

- Checkout master locally: `git checkout master; git pull; git fetch`
- Merge PR into master: `git merge release-1.1.1; git push`
- Update github release page: https://github.com/ashleygould/aws-stakermods/releases
  Use the contents of the latest CHANGELOG entry for the body.

# Helper to create CHANGELOG entries
git log --reverse --pretty=format:"%s" | tail -100 | sed 's/^/- /'

