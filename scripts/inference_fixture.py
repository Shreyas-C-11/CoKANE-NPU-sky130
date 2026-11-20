"""Synthetic signed-integer fixture and direct (output-major) tensor oracle."""
import hashlib,json,pathlib,random

def clamp(x): return min(31,max(-32,x))

def convolution_pool(image,width,height,cin,cout,bits,tables):
    depth=1<<bits; ow=width-2; oh=height-2; result=[]
    for oc in range(cout):
        convolution=[]
        for y in range(oh):
            row=[]
            for x in range(ow):
                total=0
                for ic in range(cin):
                    for ky in range(3):
                        for kx in range(3):
                            value=image[(ic*height+y+ky)*width+x+kx]
                            function=((oc*cin+ic)*3+ky)*3+kx
                            total+=tables[function*depth+(value&(depth-1))]
                row.append(clamp(total))
            convolution.append(row)
        for y in range(0,oh-1,2):
            for x in range(0,ow-1,2):
                result.append(max(convolution[y][x],convolution[y][x+1],
                                  convolution[y+1][x],convolution[y+1][x+1]))
    return result

def dense(features,outputs,bits,tables):
    depth=1<<bits
    return [clamp(sum(tables[(oc*len(features)+f)*depth+(x&(depth-1))]
                      for f,x in enumerate(features))) for oc in range(outputs)]

def create(seed=20261120):
    rng=random.Random(seed)
    image=[rng.randrange(-8,8) for _ in range(784)]
    conv1=[rng.randrange(-4,5) for _ in range(18*16)]
    conv2=[rng.randrange(-4,5) for _ in range(36*64)]
    head=[rng.randrange(-2,3) for _ in range(500*64)]
    a=convolution_pool(image,28,28,1,2,4,conv1)
    b=convolution_pool(a,13,13,2,2,6,conv2)
    scores=dense(b,10,6,head)
    assert len(a)==338 and len(b)==50 and len(set(scores))>=3
    return {'seed':seed,'image':image,'conv1':conv1,'conv2':conv2,'dense':head,
            'expected_a':a,'expected_b':b,'expected_scores':scores,
            'prediction':max(range(10),key=lambda i:scores[i])}

def write(directory):
    directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=True)
    fixture=create();lines=['/* Deterministic synthetic data, not trained MNIST weights. */']
    for name in ['image','conv1','conv2','dense']:
        data=fixture[name];lines.append(f'static const int8_t fixture_{name}[{len(data)}] = {{')
        lines.extend(','.join(str(x) for x in data[i:i+32])+',' for i in range(0,len(data),32))
        lines.append('};')
    (directory/'inference_fixture.h').write_text('\n'.join(lines)+'\n')
    (directory/'fixture.json').write_text(json.dumps(fixture,separators=(',',':'))+'\n')
    return fixture

if __name__=='__main__':
    import sys
    f=write(sys.argv[1]);print('SYNTHETIC_FIXTURE',f['seed'],f['expected_scores'])
