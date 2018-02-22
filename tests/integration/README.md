# Istio-wide Integration Test Framework

This framework provides a universal way to bring various components into a test environment.
Unlike [e2e tests](https://github.com/istio/istio/tree/master/tests/e2e), integration tests


## Run the demo

On a linux machine, run the following command:

```bash
tests/integration/example/integration.sh 
```

It builds mixs (mixer binary), downloads envoy binary and installs fortio binary from vendor directory
and brings these three components on local processes for two simple tests.

[Sample1](https://github.com/istio/istio/tree/master/tests/integration/example/tests/sample1) 
shows how to reuse a test cases in different test environment

[Sample2](https://github.com/istio/istio/tree/master/tests/integration/example/tests/sample2) 
shows how to reuse a test environment in different test case


### Run a single test manually

```bash
go test -v ./tests/integration/example/tests/sample1 \
-envoy_binary <envoy_binary_path> \
-envoy_start_script <envoy_start_script_path> \
-mixer_binary <mixer_binary_path> \
-fortio_binary <fortio_binary_path>
```
