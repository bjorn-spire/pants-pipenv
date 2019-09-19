# Why?

This is mostly from a conversation on Slack: https://pantsbuild.slack.com/archives/CASMF8SJ1/p1568861761000600

This was made to handle transitive 3rdparty dependencies. I want a consistent Python build and I want my dependencies to be pinned.

A somewhat frequent problem in our builds was that package A depends on the package `regex` that we don't use directly. Depending on which machine and cache pants is running it would download an existing or a newer version of `regex` because `A` didn't specify a pinned version.

This has also been a problem with Numpy for ML models. The person who trained the model only used Numpy and had a direct dependency declared. Where the model was used we also used pandas, because pandas was used we didn't declare numpy as a dependency as it was transitive to pandas. Now the numpy version would float for the second target until we figured out the problem and declared numpy as a direct dependency as well.

# How this works:

1. Add your new dependencies into pipenv as you normally would
2. Run `make` which will start a container and run pipenv install
3. Use `pipenv graph` to generat a graph of all the installed packages in your environment
4. Sort the graph to keep diffs smaller
5. Using the graph output generate `BUILD` that sets every explicitly declared package and pin each transient dependency at the same version across all packages

# Why things are done the way they are
there is some weirdness here:
1. The Pipfile.lock you use doesn’t contain a listing of which dependencies are used by other packages, so you can't walk the tree to see which packages depend on `regex`
2. The command pipenv graph will output a graph of everything, but it’s also not perfect because it doesn’t use the registered name of the package and it has no actual relationship with your lock file. It simply graphs whatever python packages you have installed (which is why I run the generation in a container and from scratch each time, despite it being slow)
2a. Not using the registered name: .post1 etc. names aren’t kept in the output from pipenv graph so I had some issues where I couldn’t map the actual version to what was output. I solved it by pinning to an older version of the package instead of trying to fix the actual problem (edited) 
3. Pipenv will not strictly pin your dependencies no matter what you tell it. I use the command to keep my versions and it’ll still upgrade things. Overall, I am happy with this as I would rather keep upgrading as I go along. But this will lead to most likely more targets getting updated than you hoped. Or manually pinning some versions. setuptools is a serial offender here
4. Pipenv is dog slow. But with these scripts I am getting the same version of al my packages everywhere so I’m fine with the odd slow pipenv cycle because it has reduced the number of flakey installs due to transitive dependencies
