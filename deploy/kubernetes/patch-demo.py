from kubernetes import client, config
import yaml
import os
import subprocess

print("Sock-Shop Demo App")
print("\t1) base v1")
print("\t2) deployment of v2 as canary")
print("\t3) canary 10%")
print("\t4) canary 50%")
print("\t5) v2 now prod")
print("\t6) experimental")
print("\t0) clean-up")
apply = input("Which step to apply [1, 2,..]: ")
if apply.isdigit():
    step = int(apply)
else:
    print("input choice, exiting")
    exit(1)

cpu_limit = "500m"

os.chdir(os.path.expanduser("~") +
         "/repos/microservices-demo/deploy/kubernetes")

if step == 0:
    if os.path.exists("step6.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step6.yaml"])
        os.remove("step6.yaml")
    if os.path.exists("step5.yaml"):
        os.remove("step5.yaml")
    if os.path.exists("step4.yaml"):
        os.remove("step4.yaml")
    if os.path.exists("step3.yaml"):
        os.remove("step3.yaml")
    if os.path.exists("step2.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step2.yaml"])
        os.remove("step2.yaml")
    if os.path.exists("step1.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step1.yaml"])
        os.remove("step1.yaml")
    exit(0)

# load current context from users .kube/config
config.load_kube_config()


def conf_virtual_service(service, step):
    if step > 1 and service in ["carts", "catalogue", "front-end", "orders", "payment", "shipping", "user"]:
        if step in (2, 5, 6):
            canary_pct = 0
        elif step == 3:
            canary_pct = 10
        else:
            canary_pct = 50
        production_pct = 100 - canary_pct
        config_vs = {
            "apiVersion": "networking.istio.io/v1alpha3",
            "kind": "VirtualService",
            "metadata": {
                    "name": service,
                    "namespace": "sock-shop"
            },
            "spec": {
                "hosts": [
                    service
                ],
                "http": [
                    {
                        "route": [
                            {
                                "destination": {
                                    "host": service,
                                    "subset": "production"
                                },
                                "weight": production_pct
                            },
                            {
                                "destination": {
                                    "host": service,
                                    "subset": "canary"
                                },
                                "weight": canary_pct
                            }
                        ]
                    }
                ]
            }
        }
        if step == 6:
            config_vs["spec"]["http"].append({
                "match": [
                    {
                        "headers": {
                            "experimental": {
                                "exact": "true"
                            }
                        }
                    }
                ],
                "route": [
                    {
                        "destination": {
                            "host": service,
                            "subset": "experimental"
                        }
                    }
                ]
            })
    else:
        config_vs = {
            "apiVersion": "networking.istio.io/v1alpha3",
            "kind": "VirtualService",
            "metadata": {
                    "name": service,
                    "namespace": "sock-shop"
            },
            "spec": {
                "hosts": [
                    service
                ],
                "http": [
                    {
                        "route": [
                            {
                                "destination": {
                                    "host": service,
                                    "subset": "production"
                                }
                            }
                        ]
                    }
                ]
            }
        }
    return config_vs


def conf_destination_rule(service, step):
    if step == 1 or service not in ["carts", "catalogue", "front-end", "orders", "payment", "shipping", "user"]:
        config_dr = {
            "apiVersion": "networking.istio.io/v1alpha3",
            "kind": "DestinationRule",
            "metadata": {
                "name": service,
                "namespace": "sock-shop"
            },
            "spec": {
                "host": service,
                "subsets": [
                    {
                        "name": "production",
                        "labels": {
                            "canary": "false"
                        }
                    }
                ]
            }
        }
    else:
        config_dr = {
            "apiVersion": "networking.istio.io/v1alpha3",
            "kind": "DestinationRule",
            "metadata": {
                "name": service,
                "namespace": "sock-shop"
            },
            "spec": {
                "host": service,
                "subsets": [
                    {
                        "name": "production",
                        "labels": {
                            "canary": "false"
                        }
                    },
                    {
                        "name": "canary",
                        "labels": {
                            "canary": "true"
                        }
                    }
                ]
            }
        }
    if step == 6:
        config_dr["spec"]["subsets"].append({
            "name": "experimental",
            "labels": {
                "experimental": "true"
            }
        })
    return config_dr


in_file = open("complete-demo.yaml", "r")
out1 = open("step1.yaml", "w")
if step > 1:
    out2 = open("step2.yaml", "w")
if step > 2:
    out3 = open("step3.yaml", "w")
if step > 3:
    out4 = open("step4.yaml", "w")
if step > 4:
    out5 = open("step5.yaml", "w")
if step > 5:
    out6 = open("step6.yaml", "w")

# add namespace
config_ns = {
    "apiVersion": "v1",
    "kind": "Namespace",
    "metadata": {
        "name": "sock-shop",
        "labels": {
            "field.cattle.io/projectId": "p-dqhfc",
            "istio-injection": "enabled"
        }
    }
}
yaml.dump(config_ns, out1)
out1.write("---\n")

# add istio gateway
config_gw = {
    "apiVersion": "networking.istio.io/v1alpha3",
    "kind": "Gateway",
    "metadata": {
        "name": "sock-shop-gateway",
        "namespace": "sock-shop"
    },
    "spec": {
        "selector": {
            "istio": "ingressgateway"
        },
        "servers": [
            {
                "port": {
                    "number": 80,
                    "name": "http",
                    "protocol": "HTTP"
                },
                "hosts": [
                    "sock-shop/www.10.219.246.243.xip.io"
                ]
            }
        ]
    }
}
yaml.dump(config_gw, out1)
out1.write("---\n")

# add entry virtual service (round-robin)
config_vs = {
    "apiVersion": "networking.istio.io/v1alpha3",
    "kind": "DestinationRule",
    "metadata": {
        "name": "front-end",
        "namespace": "sock-shop"
    },
    "spec": {
        "host": "front-end",
        "subsets": [
            {
                "name": "production",
                "labels": {
                    "canary": "false"
                }
            }
        ]
    }
}
yaml.dump(config_vs, out1)
out1.write("---\n")

config_vs = {
    "apiVersion": "networking.istio.io/v1alpha3",
    "kind": "VirtualService",
    "metadata": {
        "name": "sock-shop",
        "namespace": "sock-shop"
    },
    "spec": {
        "hosts": [
            "*"
        ],
        "gateways": [
            "sock-shop-gateway"
        ],
        "http": [
            {
                "route": [
                    {
                        "destination": {
                            "host": "front-end",
                            "subset": "production"
                        }
                    }
                ]
            }
        ]
    }
}
yaml.dump(config_vs, out1)
out1.write("---\n")

if step == 6:
    config_vs["spec"]["http"].insert(0, {
        "match": [
            {
                "headers": {
                    "experimental": {
                        "exact": "true"
                    }
                }
            }
        ],
        "route": [
            {
                "destination": {
                    "host": "front-end",
                    "subset": "experimental"
                }
            }
        ]
    })
    yaml.dump(config_vs, out6)
    out6.write("---\n")


configs = yaml.load_all(in_file, Loader=yaml.FullLoader)
for config in configs:
    app = config["metadata"]["name"]
    kind = config["kind"]
    if kind == "Deployment":
        # add deployments
        # - fix api version (demo project is 3+ years old)
        # - replace labels with proper ones for istio
        # - fix missing selector (demo project is 3+ years old)
        # - limit demo service cpu resources and istio sidecar resources
        # - fix zipkin namespace
        config_dep = config
        config_dep["apiVersion"] = "apps/v1"
        config_dep["metadata"]["name"] = app + "-v1"
        config_dep["metadata"]["labels"] = {
            "app": app, "version": "v1", "canary": "false"}
        config_dep["spec"]["selector"] = {
            "matchLabels": {"app": app, "version": "v1"}}
        config_dep["spec"]["template"]["metadata"]["labels"] = {
            "app": app, "version": "v1", "canary": "false"}
        config_dep["spec"]["template"]["metadata"]["annotations"] = {
            "sidecar.istio.io/proxyCPU": "10m", "sidecar.istio.io/proxyCPULimit": "500m", "sidecar.istio.io/proxyMemory": "64Mi", "sidecar.istio.io/proxyMemoryLimit": "512Mi"}
        config_dep["spec"]["template"]["spec"]["containers"][0]["resources"] = {
            "limits": {"cpu": cpu_limit}, "requests": {"cpu": "10m"}}
        if app in ["carts", "orders", "shipping"]:
            config_dep["spec"]["template"]["spec"]["containers"][0]["env"][0]["value"] = "zipkin.istio-system.svc.cluster.local"
        yaml.dump(config_dep, out1)
        out1.write("---\n")
        if step >= 5 and app in ["carts", "catalogue", "front-end", "orders", "payment", "shipping", "user"]:
            yaml.dump(config_dep, out5)
            out5.write("---\n")
        config_dr = conf_destination_rule(app, 1)
        yaml.dump(config_dr, out1)
        out1.write("---\n")
        if step > 1:
            config_dr = conf_destination_rule(app, 2)
            yaml.dump(config_dr, out2)
            out2.write("---\n")
        if step == 6 and app == "front-end":
            config_dr = conf_destination_rule(app, 6)
            yaml.dump(config_dr, out6)
            out6.write("---\n")
        config_vs = conf_virtual_service(app, 1)
        yaml.dump(config_vs, out1)
        out1.write("---\n")
        if step == 2:
            config_vs = conf_virtual_service(app, 2)
            yaml.dump(config_vs, out2)
            out2.write("---\n")
        if step == 3:
            config_vs = conf_virtual_service(app, 3)
            yaml.dump(config_vs, out3)
            out3.write("---\n")
        if step == 4:
            config_vs = conf_virtual_service(app, 4)
            yaml.dump(config_vs, out4)
            out4.write("---\n")
        if step > 1 and app in ["carts", "catalogue", "front-end", "orders", "payment", "shipping", "user"]:
            # add v2 deployments
            config_dep["metadata"]["name"] = app + "-v2"
            config_dep["spec"]["selector"] = {
                "matchLabels": {"app": app, "version": "v2"}}
            if step >= 5:
                config_dep["metadata"]["labels"] = {
                    "app": app, "version": "v2", "canary": "false"}
                config_dep["spec"]["template"]["metadata"]["labels"] = {
                    "app": app, "version": "v2", "canary": "false"}
            else:
                config_dep["metadata"]["labels"] = {
                    "app": app, "version": "v2", "canary": "true"}
                config_dep["spec"]["template"]["metadata"]["labels"] = {
                    "app": app, "version": "v2", "canary": "true"}
            yaml.dump(config_dep, out2)
            out2.write("---\n")
        if step == 6 and app == "front-end":
            # add v2 deployments
            config_dep["metadata"]["name"] = app + "-v3"
            config_dep["spec"]["selector"] = {
                "matchLabels": {"app": app, "version": "v3"}}
            config_dep["metadata"]["labels"] = {
                "app": app, "version": "v3", "experimental": "true"}
            config_dep["spec"]["template"]["metadata"]["labels"] = {
                "app": app, "version": "v3", "experimental": "true"}
            yaml.dump(config_dep, out6)
            out6.write("---\n")
    elif kind == "Service":
        # add services
        config_svc = config
        config_svc["metadata"]["labels"] = {"app": app, "service": app}
        if app == "front-end":
            config_svc["spec"]["ports"] = [{"port": 80, "targetPort": 8079}]
            del config_svc["spec"]["type"]
        config_svc["spec"]["selector"] = {"app": app}
        port = config_svc["spec"]["ports"][0]["port"]
        if port == 80:
            prot = "http"
        elif port == 27017:
            prot = "mongodb"
        elif port == 3306:
            prot = "mysql"
        elif port == 5672:
            prot = "amqp"
        else:
            prot = "tcp"
        config_svc["spec"]["ports"][0]["appProtocol"] = prot
        yaml.dump(config_svc, out1)
        out1.write("---\n")

out1.close()
try:
    out2.close()
    out3.close()
    out4.close()
    out5.close()
    out6.close()
except NameError:
    pass
in_file.close()

if apply.upper() == "1":
    if os.path.exists("step2.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step2.yaml"])
        os.remove("step2.yaml")
    if os.path.exists("step3.yaml"):
        os.remove("step3.yaml")
    if os.path.exists("step4.yaml"):
        os.remove("step4.yaml")
    if os.path.exists("step5.yaml"):
        os.remove("step5.yaml")
    if os.path.exists("step6.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step6.yaml"])
        os.remove("step6.yaml")
    subprocess.run(["kubectl", "apply", "-f", "step1.yaml"])
if apply.upper() == "2":
    if os.path.exists("step3.yaml"):
        os.remove("step3.yaml")
    if os.path.exists("step4.yaml"):
        os.remove("step4.yaml")
    if os.path.exists("step5.yaml"):
        os.remove("step5.yaml")
    if os.path.exists("step6.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step6.yaml"])
        os.remove("step6.yaml")
    subprocess.run(["kubectl", "apply", "-f", "step1.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step2.yaml"])
if apply.upper() == "3":
    if os.path.exists("step4.yaml"):
        os.remove("step4.yaml")
    if os.path.exists("step5.yaml"):
        os.remove("step5.yaml")
    if os.path.exists("step6.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step6.yaml"])
        os.remove("step6.yaml")
    subprocess.run(["kubectl", "apply", "-f", "step1.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step2.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step3.yaml"])
if apply.upper() == "4":
    if os.path.exists("step5.yaml"):
        os.remove("step5.yaml")
    if os.path.exists("step6.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step6.yaml"])
        os.remove("step6.yaml")
    subprocess.run(["kubectl", "apply", "-f", "step1.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step2.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step4.yaml"])
if apply.upper() == "5":
    if os.path.exists("step6.yaml"):
        subprocess.run(["kubectl", "delete", "-f", "step6.yaml"])
        os.remove("step6.yaml")
    subprocess.run(["kubectl", "apply", "-f", "step1.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step2.yaml"])
    subprocess.run(["kubectl", "delete", "-f", "step5.yaml"])
if apply.upper() == "6":
    if os.path.exists("step3.yaml"):
        os.remove("step3.yaml")
    if os.path.exists("step4.yaml"):
        os.remove("step4.yaml")
    subprocess.run(["kubectl", "apply", "-f", "step1.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step2.yaml"])
    subprocess.run(["kubectl", "delete", "-f", "step5.yaml"])
    subprocess.run(["kubectl", "apply", "-f", "step6.yaml"])
