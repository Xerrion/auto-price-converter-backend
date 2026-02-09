# Changelog

## [0.1.1](https://github.com/Xerrion/auto-price-converter-backend/compare/v0.1.0...v0.1.1) (2026-02-09)


### Features

* add external scheduler mode for serverless deployments ([083031f](https://github.com/Xerrion/auto-price-converter-backend/commit/083031f68492bb89af0ae5acee6bf0ad95c71d5f))
* add GitHub Actions cron for daily rate syncing ([6d67826](https://github.com/Xerrion/auto-price-converter-backend/commit/6d67826654a4e0936b7b310df4d9795e5184bba4))
* add Railway deployment configuration ([1b8460a](https://github.com/Xerrion/auto-price-converter-backend/commit/1b8460a7df129659f1935ba81f0d154eb16628df))
* add RLS policies for secure database access ([09fa767](https://github.com/Xerrion/auto-price-converter-backend/commit/09fa767e991e281fdbdfb8296a610834a6b2da47))
* add separate cache TTL for currency symbols ([290f3d9](https://github.com/Xerrion/auto-price-converter-backend/commit/290f3d9278b5fe111f468f74087df9828182c279))
* add SYMBOLS_CACHE_HOURS config for separate symbols TTL ([9e16dee](https://github.com/Xerrion/auto-price-converter-backend/commit/9e16dee21dc1d518d15936bae7698ce943878bc6))
* implement clean architecture for FastAPI backend ([58403fe](https://github.com/Xerrion/auto-price-converter-backend/commit/58403fe054f4f32f98bb972d5bc0177262628156))


### Bug Fixes

* add explicit servers to OpenAPI schema for Swagger UI ([472e4fc](https://github.com/Xerrion/auto-price-converter-backend/commit/472e4fc37f8b03ccbb4c588a3e04c654889d370b))
* add production server URL to OpenAPI docs ([#3](https://github.com/Xerrion/auto-price-converter-backend/issues/3)) ([91690ed](https://github.com/Xerrion/auto-price-converter-backend/commit/91690ed028ba1befc1f5b0ae65c74a1c3d39630e))
* enable API key authentication in Swagger UI ([d46664b](https://github.com/Xerrion/auto-price-converter-backend/commit/d46664bf9a3e0a47e74b2323ccc5b6133ac9aaa8))


### Code Refactoring

* remove scheduler, add comprehensive test suite ([ca03eac](https://github.com/Xerrion/auto-price-converter-backend/commit/ca03eaca34d701f7db84f1aa81989a70177a2e52))
* use proper FastAPI response models for type safety ([4650bbf](https://github.com/Xerrion/auto-price-converter-backend/commit/4650bbf7b16425dec4a9bf31a1cdf256d7cb5fea))
* use separate symbols cache TTL for SymbolsRepository ([726a5eb](https://github.com/Xerrion/auto-price-converter-backend/commit/726a5ebf25522c9181493ebcb763d1630fd12164))
