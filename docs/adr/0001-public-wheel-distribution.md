# Distribute a complete application as a Python wheel

Installations may use restricted package indexes and lack Node.js or frontend
build tools. Ship the application and prepared browser assets together in a
Python wheel, with the human and agent guides available as package resources.

Configuration, credentials and user research belong outside the installed
package. Runtime dependencies are supplied by the approved package index or a
prepared wheelhouse. The source archive includes the material needed to build
and verify a release without cloning its GitHub repository.
