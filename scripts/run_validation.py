import re
from validate_terraform import (
    TerraformConfig, Variable, Output, Resource, DataSource, ProviderConfig,
    BackendConfig, LocalsBlock, validate_terraform, TAGGABLE_RESOURCES, STATEFUL_RESOURCES
)

# Read Terraform configuration file
with open("terraform_config.tf", "r") as f:
    tf_text = f.read()

# Parse variables
variables = []
variable_pattern = r'^variable\s+"([^"]+)"\s*\{[^}]*?description\s*=\s*"([^"]+)"[^}]*?type\s*=\s*(\S+)[^}]*?\}'
for match in re.finditer(variable_pattern, tf_text, re.MULTILINE | re.DOTALL):
    name = match.group(1)
    description = match.group(2)
    type_str = match.group(3)
    variables.append(Variable(name=name, description=description, type=type_str))

# Parse outputs
outputs = []
output_pattern = r'^output\s+"([^"]+)"\s*\{[^}]*?description\s*=\s*"([^"]+)"[^}]*?value\s*=\s*(\S+)[^}]*?\}'
for match in re.finditer(output_pattern, tf_text, re.MULTILINE | re.DOTALL):
    name = match.group(1)
    description = match.group(2)
    value = match.group(3)
    outputs.append(Output(name=name, value=value, description=description))

# Parse resources
resources = []
resource_pattern = r'^resource\s+"([^"]+)"\s+"([^"]+)"\s*\{[^}]*?tags\s*=\s*\{[^}]*?\}'
for match in re.finditer(resource_pattern, tf_text, re.MULTILINE | re.DOTALL):
    resource_type = match.group(1)
    resource_name = match.group(2)
    resources.append(Resource(
        type=resource_type,
        name=resource_name,
        has_tags=True
    ))

# Parse data sources
data_sources = []
data_source_pattern = r'^data\s+"([^"]+)"\s+"([^"]+)"\s*\{'
for match in re.finditer(data_source_pattern, tf_text, re.MULTILINE):
    data_type = match.group(1)
    data_name = match.group(2)
    data_sources.append(DataSource(type=data_type, name=data_name))

# Parse provider version
provider_version = None
required_version = None

if "required_providers" in tf_text:
    import re
    match = re.search(r'required_providers[^}]*aws[^}]*version\s*=\s*"([^"]+)"', tf_text, re.MULTILINE | re.DOTALL)
    if match:
        provider_version = match.group(1)

# Parse backend
backend_type = None
backend_pattern = r'backend\s+"([^"]+)"'
backend_match = re.search(backend_pattern, tf_text)
if backend_match:
    backend_type = backend_match.group(1)

# Parse locals
locals_entries = {}
locals_pattern = r'locals\s*\{\s*([^}]+?)\}'
locals_match = re.search(locals_pattern, tf_text, re.MULTILINE | re.DOTALL)
if locals_match:
    locals_content = locals_match.group(1)
    # Extract key=value pairs
    for entry in locals_content.split('\n'):
        if '=' in entry and not entry.strip().startswith('#'):
            key, value = entry.split('=', 1)
            locals_entries[key.strip()] = value.strip()

# Construct TerraformConfig
config = TerraformConfig(
    provider=ProviderConfig(
        provider="aws",
        version_constraint=provider_version,
        required_version=required_version
    ),
    backend=BackendConfig(
        backend_type=backend_type
    ),
    variables=variables,
    outputs=outputs,
    resources=resources,
    data_sources=data_sources,
    locals=LocalsBlock(entries=locals_entries) if locals_entries else None
)

# Task requirements
task = {
    "requirements": {
        "sensitive_values": False,
        "data_sources": True  # Using aws_ami data source
    }
}

# Run validation
results = validate_terraform(config, tf_text, task)

# Print results
print("=" * 80)
print("TERRAFORM VALIDATION RESULTS")
print("=" * 80)
print()

passed = 0
failed = 0
needs_review = 0

for rule_name, passed_rule, detail in results:
    if passed_rule:
        passed += 1
        status = "✓ PASS"
    elif detail == "needs_review":
        needs_review += 1
        status = "○ REVIEW"
    else:
        failed += 1
        status = "✗ FAIL"

    print(f"{status} [{rule_name}]")
    print(f"  Detail: {detail}")
    print()

print("=" * 80)
print(f"SUMMARY: {passed} passed, {failed} failed, {needs_review} needs review")
print("=" * 80)

if failed == 0:
    print("\n✓ All required checks passed!")
else:
    print(f"\n✗ {failed} check(s) failed. Please review the details above.")
