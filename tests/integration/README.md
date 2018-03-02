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

One example:
```bash
go test -v ./tests/integration/example/tests/sample1
-envoy_binary /home/bootstrap/go/out/linux_amd64/release/envoy \
-envoy_start_script /home/bootstrap/go/src/istio.io/proxy/src/envoy/http/mixer/start_envoy \
-mixer_binary /home/bootstrap/go/out/linux_amd64/release/mixs \
-fortio_binary fortio
```


### File Structure
Under istio/tests/integration directory, it has three top level folders: **component, framework and example**.

* **component** is a centralized locations for existing components. New reusable components should be put here.

* **framework** has structures and interfaces for this integration test framework.
* **example** is a folder with demo showing how to use this framework. Developers can add their own tests based on the structure in the folder.

    * integration.sh is the entry script to build and trigger tests.
    * tests contains test files.
    * environment contains TestEnv implementations for tests here.


### Add tests
#### Find the components or create new ones

Based on what modules you need (mixer, proxy and/or some applications) to test
and where you want to set up those modules (local process, local kube or actual kubernetes cluster),
one or more componensare required.

We have a centralized location [istio/tests/integration/components](https://github.com/istio/istio/tree/master/tests/integration/component)
to keep components for reuse in different cases.
It is advisable to reuse existing components if possible.
Also, you can update existing components to satisfy your requirement as long as the change is backward compatible and
does not break existing tests.  If you cannot find a component to reuse, you can create your own and put it in the same components directory
if it is intended to be reused by other developers or test cases.

* A component must implement Component interface with all methods:

    * `GetName()`: GetName return component name. This enforce every component to have a name.

    * `Start()`: Start defines how to step up and start this component. Will be called in testEnvManager.SetUp()

    * `Stop()`: Stop defines how to stop this component. Will be called in testEnvManager.TearDown()

    * `IsAlive()`: This is a method to check if this component is alive and working properly. It’s way to monitor if it’s being successfully started/stopped.

    * `GetConfig()`: GetConfig returns the config of this component for outside use. It can be called anytime during the whole component lifetime. It's recommended to use sync. Mutex to lock data while read in case component itself is accessing config.

    * `SetConfig(config Config)`: SetConfig sets a config into this component. Initial config is set when during initialization. But config can be updated at runtime using SetConfig. Component needs to implement extra functions to apply new configs. It's recommended to use sync.Mutex to lock data while write in case component itself is accessing config.

    * `GetStatus()`: GetStatus returns the status of this component for outside use. It can be called anytime during the whole component lifetime. It's recommended to use sync.Mutex to lock data while read in case component itself is updating status.

* Life cycle of a component:  
    * Components are defined in a environment by create an instance in GetComponents() []framework.Component.

    * In TestEnvManager.StartUp() components will be triggered to start at once, and then TestEnvManager.WaitUntilReady() is going to check if everything is ready. If not, it will wait and retry several times before either the entire environment is ready or still fail after multiple attempts and throw an error.

    * Components will be stopped and cleanup in testEnvManager.TearDown() when either tests finished or got interrupted by an error.

#### Create a test environment

Create a test environment and define what components are included.

* A environment must implement environment interface with all methods:

    * `GetComponents()`: The key part, this method bakes components in this environment and returns them in a list.

    * `GetName()`: GetName return environment name. This enforce every environment to have a name.

    * `Bringup()`: Preparations should be done for the whole environment

    * `Cleanup()`: Clean everything created by this test environment, not component level
