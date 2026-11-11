"""Verify a clean Flamel Python environment without running scientific experiments."""
from __future__ import annotations
import argparse,base64,csv,hashlib,importlib.metadata as md,io,json,os,pathlib,platform,re,sys

def normalize(name):
    return re.sub(r"[-_.]+","-",name).lower()

def expected_pins(path, environment):
    result={}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line=line.strip()
        if not line or line.startswith("#"):continue
        if "==" in line:
            name,version=line.split("==",1);result[normalize(name)]=version
        elif line.startswith("torch @ "):
            result["torch"]="2.15.0+cpu" if environment=="analysis-maintenance-cpu" else "2.6.0+cu124"
    if environment=="generator-historical":result["crystalformer"]="0.6"
    return result

def verify_record_file(path,distribution):
    """Check packaged checkpoint bytes against the fresh distribution's RECORD."""
    dist=md.distribution(distribution)
    content=dist.read_text("RECORD")
    if not content:raise RuntimeError("Missing package RECORD")
    for row in csv.reader(io.StringIO(content)):
        candidate=pathlib.Path(dist.locate_file(row[0])).resolve()
        if candidate==path.resolve():
            kind,encoded=row[1].split("=",1)
            if kind!="sha256":raise RuntimeError("Checkpoint requires SHA256 record")
            actual=hashlib.sha256(path.read_bytes()).digest()
            if base64.urlsafe_b64encode(actual).rstrip(b"=").decode()!=encoded:raise RuntimeError("Checkpoint RECORD mismatch")
            return hashlib.sha256(path.read_bytes()).hexdigest()
    raise RuntimeError("Checkpoint not present in package RECORD")

def verify_packaged_chgnet_checkpoint(path):
    digest=verify_record_file(path,"chgnet")
    if digest!="d14ab7c0f093efe64b60a7bcd540bca10e74fb7f46c86108a079af60524659d1":
        raise RuntimeError("Checkpoint differs from the explicitly pinned CHGNet0.3.0 bytes")
    return digest

def verify(spec,environment,load_trusted_chgnet=False):
    expected=expected_pins(spec,environment)
    installed={normalize(dist.metadata["Name"]):dist.version for dist in md.distributions()}
    mismatches=[{"name":name,"expected":version,"actual":installed.get(name)} for name,version in expected.items() if installed.get(name)!=version]
    undeclared=sorted(set(installed)-set(expected))
    if mismatches or undeclared:raise RuntimeError("Installed environment differs from exact specification")
    if sys.version_info[:3]!=(3,11,14):raise RuntimeError("Expected Python 3.11.14")
    imports={}
    import numpy as np,pandas as pd,ase,scipy,pymatgen,matplotlib
    matplotlib.use("Agg")
    from pymatgen.core import Lattice,Structure
    structure=Structure(Lattice.cubic(4.2),["Mg","O"],[[0,0,0],[.5,.5,.5]])
    assert len(structure)==2
    assert (np.array([1,2])+np.array([3,4])).tolist()==[4,6]
    assert pd.DataFrame({"a":[1,2]}).a.sum()==3
    imports["base_materials_stack"]="PASS"
    trusted_checkpoint=None
    if environment.startswith("analysis"):
        import sklearn,torch,filelock,chgnet
        assert torch.tensor([1.0,2.0]).sum().item()==3.0
        imports["analysis_stack"]="PASS"
        imports["torch_version"]=torch.__version__
        imports["torch_cuda_build"]=torch.version.cuda
        imports["torch_cuda_available"]=torch.cuda.is_available()
        if load_trusted_chgnet:
            if environment!="analysis-maintenance-cpu":raise RuntimeError("Model-load check is restricted to maintenance CPU environment")
            checkpoint=pathlib.Path(chgnet.__file__).parent/"pretrained"/"0.3.0"/"chgnet_0.3.0_e29f68s314m37.pth.tar"
            if not checkpoint.exists():
                candidates=list((pathlib.Path(chgnet.__file__).parent/"pretrained"/"0.3.0").glob("*.pth.tar"))
                if len(candidates)!=1:raise RuntimeError("Expected exactly one packaged trusted checkpoint")
                checkpoint=candidates[0]
            digest=verify_packaged_chgnet_checkpoint(checkpoint)
            from chgnet.model.model import CHGNet
            model=CHGNet.load(model_name="0.3.0",use_device="cpu",verbose=False)
            assert str(next(model.parameters()).device)=="cpu"
            trusted_checkpoint={"source":"Fresh official PyPI CHGNet0.4.2 package, installed wheel RECORD SHA256 checked before load","sha256":digest,"model":"0.3.0","device":"cpu","loaded":True,"inference_or_relaxation_run":False}
    else:
        import jax,jax.numpy as jnp,haiku,optax,pyxtal,crystalformer
        assert jnp.add(jnp.array([1,2]),jnp.array([3,4])).tolist()==[4,6]
        imports["generator_stack"]="PASS";imports["jax_backend"]=jax.default_backend();imports["jax_devices"]=[str(device) for device in jax.devices()]
        resource_hashes={}
        for filename,expected_sha in {
            "wyckoff_list.csv":"712a7b3cd23f1aaffd90cbae6531809bfe686fef042bcc6c4b1549bc4e2ec3c6",
            "wyckoff_symbols.csv":"035035df9fb581f1a0955da371feb1cdee8034d875b432405090254dfef43fd0",
        }.items():
            resource=pathlib.Path(crystalformer.__file__).parent/"data"/filename
            digest=hashlib.sha256(resource.read_bytes()).hexdigest()
            if digest!=expected_sha:raise RuntimeError("Installed CrystalFormer data differs from the pinned source")
            resource_hashes[filename]=digest
        imports["crystalformer_resource_hashes"]=resource_hashes
    return {"result":"PASS","environment":environment,"python":sys.version,"executable":sys.executable,"prefix":sys.prefix,"base_prefix":sys.base_prefix,"platform":platform.platform(),"package_count":len(installed),"packages":installed,"mismatches":mismatches,"undeclared_packages":undeclared,"imports":imports,"trusted_chgnet_checkpoint":trusted_checkpoint,"scientific_experiments_run":False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec",type=pathlib.Path,required=True)
    parser.add_argument("--environment",choices=["analysis-historical","generator-historical","analysis-maintenance-cpu"],required=True)
    parser.add_argument("--load-trusted-chgnet",action="store_true")
    parser.add_argument("--report",type=pathlib.Path,required=True)
    args=parser.parse_args()
    target=args.report.absolute()
    source_root=pathlib.Path(__file__).resolve().parents[2]
    if target.exists() or target.resolve().is_relative_to(source_root) or target.resolve().is_relative_to(pathlib.Path(sys.prefix).resolve()):
        raise ValueError("Use a new report outside source and the installed environment")
    for parent in target.parents:
        if parent.exists() and (parent.is_symlink() or getattr(parent.lstat(),"st_file_attributes",0)&0x400):
            raise ValueError("Report ancestor is a reparse point")
    result=verify(args.spec,args.environment,args.load_trusted_chgnet)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("packages",)}))
    return 0
if __name__=="__main__":raise SystemExit(main())
