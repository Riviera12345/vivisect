import sys
import envi
import envi.memory as e_mem
import envi.memcanvas as e_memcanvas
import envi.memcanvas.renderers as e_rend
import envi.archs.amd64 as e_amd64
import vivisect
import platform
import unittest

instrs = [
    ("bf9fb44900", 0x456000, 'mov edi,0x0049b49f'),
    ("48bf9fb44900aabbccdd", 0x456000, 'mov rdi,0xddccbbaa0049b49f'),
    ("c705b58a270001000000", 0x456005, 'mov dword [rip + 2591413],1'),
    ("48c705e68a270084ef4a00", 0x45600f, 'mov qword [rip + 2591462],0x004aef84'),
    ("48c705b39b2700105f4500", 0x45601a, 'mov qword [rip + 2595763],0x00455f10'),
    ('c4e2f1004141', 0x456000, 'vpshufb xmm0,xmm1,oword [rcx + 65]'),
    ('c4e2f5004141', 0x456000, 'vpshufb ymm0,ymm1,yword [rcx + 65]'),
    ('0f38004141', 0x456000, 'pshufb mm0,qword [rcx + 65]'),
    ("41b401", 0x456000, 'mov r12l, 1'),      # ndisasm and oda say "mov r12b, 1" but ia32 manual says "r12l"
    ("4585f6", 0x456000, 'test r14d,r14d'),
]


class Amd64InstrTest(unittest.TestCase):
    def test_envi_amd64_assorted_instrs(self):
        global instrs

        archmod = envi.getArchModule("amd64")

        for bytez, va, reprOp in instrs:
            op = archmod.archParseOpcode(bytez.decode('hex'), 0, va)
            if repr(op).replace(' ', '') != reprOp.replace(' ', ''):
                raise Exception("FAILED to decode instr:  %.8x %s - should be: %s  - is: %s" %
                                (va, bytez, reprOp, repr(op)))

    # FIXME: test emuluation as well.


# name, bytes, va, repr, txtRender
amd64SingleByteOpcodes = [
    ('add', '0001', 'add byte [rcx],al', 'add byte [rcx],al'),
    ('jg', '7faa', 'jg 0x000003ac', 'jg 0x000003ac'),
    ('rep movsb', 'f3a4', 'rep: movsb ', 'rep: movsb '),
    ('mov al', 'b0aa', 'mov al,170', 'mov al,170'),
    ('mov ebx', 'b8aaaa4040', 'mov eax,0x4040aaaa', 'mov eax,0x4040aaaa'),
    ('call ebx', 'ffd3', 'call rbx', 'call rbx'),
    ('call lit', 'e801010101', 'call 0x01010146', 'call 0x01010146'),
    ('mov dword', '89aa41414141', 'mov dword [rdx + 1094795585],ebp', 'mov dword [rdx + 1094795585],ebp'),
    ('imul 1', 'f6aaaaaaaaaa', 'imul al,byte [rdx - 1431655766]', 'imul al,byte [rdx - 1431655766]'),
    ('imul 2', 'f7aaaaaaaaaa', 'imul eax,dword [rdx - 1431655766]', 'imul eax,dword [rdx - 1431655766]'),
    ('push', 'fff0', 'push eax', 'push eax'),
    ('pop', '8ff0', 'pop eax', 'pop eax'),
    ('pop', '8ffb', 'pop ebx', 'pop ebx'),
    ('push', '48fff0', 'push rax', 'push rax'),
    ('pop', '488ff0', 'pop rax', 'pop rax'),
    ('pop', '488ffb', 'pop rbx', 'pop rbx'),
    ('ud2', '0f0b', 'ud2 ', 'ud2 '),
    ('FISTTP', 'db08', 'fisttp dword [rax]', 'fisttp dword [rax]'),
    ('FISTTP', 'df08', 'fisttp word [rax]', 'fisttp dword [rax]'),
    ('FISTTP', 'dd08', 'fisttp qword [rax]', 'fisttp dword [rax]'),
    ('FDIV', 'd8f1', 'fdiv s0,st1', 'fdiv s0,st1'),
    ('FXCH', 'd9ca', 'fxch st0,st2', 'fxch st0,st2'),
    ('FADDP', 'dec1', 'faddp st1,st0', 'faddp st1,st0'),
    ('PREFETCH0', '0f1809', 'prefetch0 byte [rcx]', 'prefetch0 byte [rcx]'),
    ('PREFETCH1', '0f1810', 'prefetch1 byte [rax]', 'prefetch1 byte [rax]'),
    ('PREFETCH2', '0f181b', 'prefetch2 byte [rbx]', 'prefetch2 byte [rbx]'),
    ('PREFETCHNTA', '0f1802', 'prefetchnta byte [rdx]', 'prefetchnta byte [rdx]'),
    ('PREFETCH0', '670f1809', 'prefetch0 byte [ecx]', 'prefetch0 byte [ecx]'),
    ('PREFETCH1', '670f1810', 'prefetch1 byte [eax]', 'prefetch1 byte [eax]'),
    ('PREFETCH2', '670f181b', 'prefetch2 byte [ebx]', 'prefetch2 byte [ebx]'),
    ('PREFETCHNTA', '670f1802', 'prefetchnta byte [edx]', 'prefetchnta byte [edx]'),
    # ('CDQE', '4898', 'cdqe ', 'cdqe '), # It bothers me that this doesn't work
    ('BSWAP (eax)', 'f30fc84141', 'rep: bswap eax', 'rep: bswap eax'),
]

amd64MultiByteOpcodes = [
    ('NOT', '66F7D0', 'not ax', 'not ax'),
    ('NOT 2', 'F7D0', 'not eax', 'not eax'),
    ('PUSH', '6653', 'push bx', 'push bx'),
    #('PUSH 2', '67FF37', 'push qword [edi]', 'push dword [edi]'),
    #('MOV w/ size', '67488B16', 'mov rdx,qword [esi]', 'mov rdx,qword [esi]'),
    #('HSUBPS', '67F20F7D9041414141', 'hsubps xmm1,oword [eax + 0x41414141]', 'hsubps xmm1,oword [eax + 0x41414141]'),
    ('HSUBPS 2', 'F20F7D9041414141', 'hsubps xmm2,oword [rax + 1094795585]', 'hsubps xmm2,oword [rax + 1094795585]'),
    ('HSUBPS 3', 'F20F7D10', 'hsubps xmm2,oword [rax]', 'hsubps xmm2,oword [rax]'),
    #('HSUBPS 4', '67F20F7D12', 'hsubps xmm2,oword [edx]', 'hsubps xmm2,oword [edx]'),

    ('CVTTPS2PI', '0f2caaaaaaaa41', 'cvttps2pi mm5,oword [rdx + 1101703850]', 'cvttps2pi mm5,oword [rdx + 1101703850]'),
    ('CVTTSS2SI', 'f30f2caaaaaaaa41', 'cvttss2si ebp,oword [rdx + 1101703850]', 'cvttss2si ebp,oword [rdx + 1101703850]'),
    ('CVTTPD2PI', '660f2caaaaaaaa41', 'cvttpd2pi mm5,oword [rdx + 1101703850]', 'cvttpd2pi mm5,oword [rdx + 1101703850]'),
    ('CVTTSD2SI', 'f20f2caaaaaaaa41', 'cvttsd2si ebp,oword [rdx + 1101703850]', 'cvttsd2si ebp,oword [rdx + 1101703850]'),
    ('ADDPS', '0f58aa4141414141', 'addps xmm5,oword [rdx + 1094795585]', 'addps xmm5,oword [rdx + 1094795585]'),
    ('MOVAPS', '0f28aa41414141', 'movaps xmm5,oword [rdx + 1094795585]', 'movaps xmm5,oword [rdx + 1094795585]'),
    ('MOVAPD', '660f28aa41414141', 'movapd xmm5,oword [rdx + 1094795585]', 'movapd xmm5,oword [rdx + 1094795585]'),
    ('PMULLW (66)', '660faa41414141', 'rsm ', 'rsm '),
    ('CMPXCH8B', '0fc70a', 'cmpxch8b qword [rdx]', 'cmpxch8b qword [rdx]'),
    ('MOVD (66)',   '660f7ecb414141', 'movd ebx,xmm1', 'movd ebx,xmm1'),
    ('MOVD', '0F6E0D41414100', 'movd mm1,dword [rip + 4276545]', 'movd mm1,dword [rip + 4276545]'),
    ('MOVQ', '0F6FCB', 'movq mm1,mm3', 'movq mm1,mm3'),
    ('PSRAW',  '0FE1CA4141', 'psraw mm1,mm2', 'psraw mm1,mm2'),
    ('PSRLQ (66)',  '660FF3CB4141', 'psllq xmm1,xmm3', 'psllq xmm1,xmm3'),
    ('PALIGNR', '0F3A0FDC03', 'palignr xmm3,xmm4,3', 'palignr xmm3,xmm4,3'),
    ('PALIGNR (66)',  '660F3A0FCA07', 'palignr xmm1,xmm2,7', 'palignr xmm1,xmm2,7'),
    ('PSLLQ (reg)',  '660FF3CA', 'psllq xmm1,xmm2', 'psllq xmm1,xmm2'),
    ('PSLLW (regs)',  '0F71F108', 'psllw mm1,8', 'psllw mm1,8'),
    ('PSLLQ (66)',  '660F73F108', 'psllq xmm1,8', 'psllq xmm1,8'),
    ('RDTSC', '0F31', 'rdtsc ', 'rdtsc '),
    ('RDTSCP', '0F01F9', 'rdtscp ', 'rdtscp '),

    ('PSRLW (66)', '660fd1ce', 'psrlw xmm1,xmm6', 'psrlw xmm1,xmm6'),
    ('PSRLW (66) 2', '660F71D611', 'psrlw xmm6,17', 'psrlw xmm6,17'),
    ('PSRLW (66) 3', '660FD10C253A3A3A3A', 'psrlw xmm1,oword [0x3a3a3a3a]', 'psrlw xmm1,oword [0x3a3a3a3a]'),
    ('PSRAD (66)', '660F72E704', 'psrad xmm7,4', 'psrad xmm7,4'),
    ('PSHUFB', '660F3800EF', 'pshufb xmm5,xmm7', 'pshufb xmm5,xmm7'),
    ('MOVBE', '0F38F0042541414141', 'movbe eax,dword [0x41414141]', 'movbe eax,dword [0x41414141]'),
    ('MOVBE 2', '0F38F10C2541414141', 'movbe dword [0x41414141],ecx', 'movbe dword [0x41414141],ecx'),
    ('PABSB', '0F381CCD', 'pabsb mm1,mm5', 'pabsb mm1,mm5'),
    ('PABSB 2', '0F381C2C2541414141', 'pabsb mm5,qword [0x41414141]', 'pabsb mm5,qword [0x41414141]'),
    ('PABSB 3', '660F381CD4', 'pabsb xmm2,xmm4', 'pabsb xmm2,xmm4'),
    ('PABSB 4', '660F381C1C2541414141', 'pabsb xmm3,oword [0x41414141]', 'pabsb xmm3,oword [0x41414141]'),
    ('POPCNT', '66f30fb8c3', 'popcnt ax,bx', 'popcnt ax,bx'),

    ('PSRLQ (66)',  '660F73D308', 'psrlq xmm3,8', 'psrlq xmm3,8'),
    ('PSRLQ 2',  '660f73d501', 'psrlq xmm5,1', 'psrlq xmm5,1'),
    ('PSRLQ', '660FD3DC', 'psrlq xmm3,xmm4', 'psrlq xmm3,xmm4'),
    ('PSRLQ', '660F73d10f', 'psrlq xmm1,15', 'psrlq xmm1,15'),
    ('PSRLDQ (66)', '660f73b5aa4141', 'psllq xmm5,170', 'psllq xmm5,170'),
    ('PSRLDQ (66)', '660f73f5aa4141', 'psllq xmm5,170', 'psllq xmm5,170'),
    ('PSRLDQ (66)', '660f73b1aa4141', 'psllq xmm1,170', 'psllq xmm1,170'),
    ('PSRLDQ (66)', '660f73b9aa4141', 'psldq xmm1,170', 'psldq xmm1,170'),
    ('PCMPISTRI', '660f3a630f0d', 'pcmpistri xmm1,oword [rdi],13', 'pcmpistri xmm1,oword [rdi],13'),

    ('POPCNT', 'f30fb8c4', 'popcnt eax,esp', 'popcnt eax,esp'),
    ('POPCNT', 'f3480fb8c4', 'popcnt rax,rsp', 'popcnt rax,rsp'),
    ('POPCNT', 'f30fb80541414100', 'popcnt eax,dword [rip + 4276545]', 'popcnt eax,dword [rip + 4276545]'),
    ('LZCNT', 'f30fbdc4', 'lzcnt eax,esp', 'lzcnt eax,esp'),
    ('LZCNT', 'f30fbd0541414100', 'lzcnt eax,dword [rip + 4276545]', 'lzcnt eax,dword [rip + 4276545]'),

    ('MOVDQU', 'F30F6FCA', 'movdqu xmm1,xmm2', 'movdqu xmm1,xmm2'),
    ('MOVDQU (MEM)', 'F30F6F4810', 'movdqu xmm1,oword [rax + 16]', 'movdqu xmm1,oword [rax + 16]'),
    ('MOVDQU (REP)', 'F3F30F6FCA', 'movdqu xmm1,xmm2', 'movdqu xmm1,xmm2'),
    ('MOVSD', 'f20f100d28330608', 'movsd xmm1,oword [rip + 134624040]', 'movsd xmm1,oword [rip + 134624040]'),
    ('MOVSD 2', 'f20f1145f0', 'movsd oword [rbp - 16],xmm0', 'movsd oword [rbp - 16],xmm0'),
    ('MOVSD 3', 'f20f100d70790908', 'movsd xmm1,oword [rip + 134838640]', 'movsd xmm1,oword [rip + 134838640]'),
    ('MOVSS', 'f30f1045f8', 'movss xmm0,dword [rbp - 8]', 'movss xmm0,dword [rbp - 8]'),
    ('MOVSS 2', 'f30f1055d0', 'movss xmm2,dword [rbp - 48]', 'movss xmm2,dword [rbp - 48]'),
    ('MOVSS 3', 'F30F110D41414100', 'movss dword [rip + 4276545],xmm1', 'movss dword [rip + 4276545],xmm1'),
    ('CVTSI2SS', 'f30f2ac8', 'cvtsi2ss xmm1,eax', 'cvtsi2ss xmm1,eax'),
    ('MULSS', 'f30f59ca', 'mulss xmm1,xmm2', 'mulss xmm1,xmm2'),
    ('SUBSS', 'f30f5cc1', 'subss xmm0,xmm1', 'subss xmm0,xmm1'),
    ('CVTSS2SD', 'f30f5ac0', 'cvtss2sd xmm0,xmm0', 'cvtss2sd xmm0,xmm0'),
    ('SQRTSS', 'f30f51d9', 'sqrtss xmm3,xmm1', 'sqrtss xmm3,xmm1'),
    ('VMXON', 'f30fc73541414100', 'vmxon qword [rip + 4276545]', 'vmxon qword [rip + 4276545]'),
    ('VMPTRST', '0FC73C2541414141', 'vmptrst qword [0x41414141]', 'vmptrst qword [0x41414141]'),
    ('VMREAD', '0F78D8', 'vmread rax,rbx', 'vmread rax,rbx'), #XXX: This will change on 32bit
    ('VMREAD 2', '0F781C2541414141', 'vmread qword [0x41414141],rbx', 'vmread qword [0x41414141],rbx'),
    ('VMWRITE', '0F79CB', 'vmwrite rcx,rbx', 'vmwrite rcx,rbx'),
    ('VMWRITE 2', '0F790C2541414141', 'vmwrite rcx,qword [0x41414141]', 'vmwrite rcx,qword [0x41414141]'),
    ('VMXOFF', '0F01C4', 'vmxoff ', 'vmxoff '),
    ('VMRESUME', '0F01C3', 'vmresume ', 'vmresume '),
    ('VMLAUNCH', '0F01C2', 'vmlaunch ', 'vmlaunch '),
    ('VMFUNC', '0F01D4', 'vmfunc ', 'vmfunc '),  # XXX: Implies eax
    ('VMCALL', '0F01C1', 'vmcall ', 'vmcall '),
    ('VMCLEAR', '660FC7342541414141', 'vmclear qword [0x41414141]', 'vmclear qword [0x41414141]'),
    ('INVVPID', '660F3881042541414141', 'invvpid rax,oword [0x41414141]', 'invvpid rax,oword [0x41414141]'),
    ('INVEPT', '660F3880142541414141', 'invept rdx,oword [0x41414141]', 'invept rdx,oword [0x41414141]'),
    ('MULSD', 'f20f59c1', 'mulsd xmm0,xmm1', 'mulsd xmm0,xmm1'),
    ('VMCLEAR', '660FC73541414100', 'vmclear qword [rip + 4276545]', 'vmclear qword [rip + 4276545]'),
    ('MOVBE',   '0F38F04910', 'movbe ecx,dword [rcx + 16]', 'movbe ecx,dword [rcx + 16]'),
    ('MOVBE 2', '0F38F009', 'movbe ecx,dword [rcx]', 'movbe ecx,dword [rcx]'),
    ('MOVBE 3', '0F38F00C8D41414141', 'movbe ecx,dword [0x41414141 + rcx * 4]', 'movbe ecx,dword [0x41414141 + rcx * 4]'),
    ('MOVBE 4', '0F38F15110', 'movbe dword [rcx + 16],edx', 'movbe dword [rcx + 16],edx'),
    ('MOVBE 5', '0F38F102', 'movbe dword [rdx],eax', 'movbe dword [rdx],eax'),
    ('MOVBE 6', '0F38F10541414141', 'movbe dword [rip + 1094795585],eax', 'movbe dword [rip + 1094795585],eax'),
    # TODO: Need to wrap in support for thing slike fstcw and fstenv, which overlap with wait
    # TODO: need to make sure 66 <REX> stuff works
    ('CRC 1', 'f20f38f0e8', 'crc32 ebp,al', 'crc32 ebp,al'),
    ('CRC 2', '66f20f38f1C3', 'crc32 eax,bx', 'crc32 eax,bx'),
    ('CRC 3', 'f20f38f1C3', 'crc32 eax,ebx', 'crc32 eax,ebx'),
    ('CLAC', '0f01ca414141', 'clac ', 'clac '),
    ('STAC', '0f01cb414141', 'stac ', 'stac '),
    ('VMFUNC', '0f01d44141', 'vmfunc ', 'vmfunc '),
    ('XEND', '0f01d54141', 'xend ', 'xend '),
    ('XGETBV', '0f01d04141', 'xgetbv ecx', 'xgetbv ecx'),
    ('XSETBV', '0f01d14141', 'xsetbv ecx', 'xsetbv ecx'),
    ('XTEST', '0f01d64141', 'xtest ', 'xtest '),
    ('MOVUPD', '660f10cc', 'movupd xmm1,xmm4', 'movupd xmm1,xmm4'),
    ('MOVUPD', '660f1018', 'movupd xmm3,oword [rax]', 'movupd xmm3,oword [rax]'),
    ('UNPCKLPD', '660F14A241414100', 'unpcklpd xmm4,oword [rdx + 4276545]', 'unpcklpd xmm4,oword [rdx + 4276545]'),
    ('UNPCKHPD', '660F15CA', 'unpckhpd xmm1,xmm2', 'unpckhpd xmm1,xmm2'),
    #('UNPCKHPD', '67660F158841414141', 'unpckhpd xmm1,oword [eax + 1094795585]', 'unpckhpd xmm1,oword [eax + 1094795585]'), TODO: This need to not be addr and actually affect the register
    ('MOVHPD', '660F162541414141', 'movhpd xmm4,qword [rip + 1094795585]', 'movhpd xmm4,qword [rip + 1094795585]'),
    ('MOVHPD', '660F172D41414141', 'movhpd qword [rip + 1094795585],xmm5', 'movhpd qword [rip + 1094795585],xmm5'),
    ('MOVMSKPS', '0F50D6', 'movmskps edx,xmm6', 'movmskps edx,xmm6'),
    ('MOVMSKPD', '660F50D6', 'movmskpd edx,xmm6', 'movmskpd edx,xmm6'),
    ('MOVHLPS', '0F12DF', 'movlps xmm3,xmm7', 'movlps xmm3,xmm7'),
    ('SUBPD', '660F5C6C240E', 'subpd xmm5,oword [rsp + 14]', 'subpd xmm5,oword [rsp + 14]'),
    ('MAXPD', '660F5FAB0F270000', 'maxpd xmm5,oword [rbx + 9999]', 'maxpd xmm5,oword [rbx + 9999]'),
    ('XORPD', '660F57BD15CD5B07', 'xorpd xmm7,oword [rbp + 123456789]', 'xorpd xmm7,oword [rbp + 123456789]'),
    ('SQRTPD', '660f51ca', 'sqrtpd xmm1,xmm2', 'sqrtpd xmm1,xmm2'),
    ('PSHUFD', '660F70CD11', 'pshufd xmm1,xmm5,17', 'pshufd xmm1,xmm5,17'),
    ('PEXTRW', '660FC5C307', 'pextrw rax,xmm3,7', 'pextrw rax,xmm3,7'),
    ('MOVQ', '660FD620', 'movq qword [rax],xmm4', 'movq qword [rax],xmm4'),
    ('PMAXUB', '660FDE2541414141', 'pmaxub xmm4,oword [rip + 1094795585]', 'pmaxub xmm4,oword [rip + 1094795585]'),
    ('MOVNTDQ', '660FE73D78563412', 'movntdq oword [rip + 305419896],xmm7', 'movntdq oword [rip + 305419896],xmm7'),
    ('PADDD', '660FFECE', 'paddd xmm1,xmm6', 'paddd xmm1,xmm6'),
    ('HADDPS', 'F20F7CCE', 'haddps xmm1,xmm6', 'haddps xmm1,xmm6'),
    ('HADDPS 1', 'C5CB7CCB', 'vhaddps xmm1,xmm6,xmm3', 'vhaddps xmm1,xmm6,xmm3'),
    ('HADDPS 2', 'C5E77CD6', 'vhaddps ymm2,ymm3,ymm6', 'vhaddps ymm2,ymm3,ymm6'),

    # override tests
    ('BSF', '480FBCC2', 'bsf rax,rdx', 'bsf rax,rdx'),
    ('BSF 2', '0FBC042541414141', 'bsf eax,dword [0x41414141]', 'bsf eax,dword [0x41414141]'),
    # AES-NI feature set
    ('AESENC', '660F38DCEA', 'aesenc xmm5,xmm2', 'aesenc xmm5,xmm2'),
    ('AESENC (MEM)', '660f38DC3A', 'aesenc xmm7,oword [rdx]', 'aesenc xmm7,oword [rdx]'),
    ('AESENC (MEM 2)', '660f38DC7C2404', 'aesenc xmm7,oword [rsp + 4]', 'aesenc xmm7,oword [rsp + 4]'),
    ('AESENC (MEM 3)', '660F38DC1D41414141', 'aesenc xmm3,oword [rip + 1094795585]', 'aesenc xmm3,oword [rip + 1094795585]'),
    ('AESENCLAST', '660F38DDDC', 'aesenclast xmm3,xmm4', 'aesenclast xmm3,xmm4'),
    ('AESENCLAST (MEM)', '660F38DD18', 'aesenclast xmm3,oword [rax]', 'aesenclast xmm3,oword [rax]'),
    ('AESENCLAST (MEM 2)', '660F38DD5808', 'aesenclast xmm3,oword [rax + 8]', 'aesenclast xmm3,oword [rax + 8]'),
    ('AESENCLAST (MEM 3)', '660F38DD2578563442', 'aesenclast xmm4,oword [rip + 1110726264]', 'aesenclast xmm4,oword [rip + 1110726264]'),
    ('AESDEC', '660f38DECB', 'aesdec xmm1,xmm3', 'aesdec xmm1,xmm3'),
    ('AESDEC (MEM)', '660F38DE0C24', 'aesdec xmm1,oword [rsp]', 'aesdec xmm1,oword [rsp]'),
    ('AESDEC (MEM 2)', '660F38DE5D0C', 'aesdec xmm3,oword [rbp + 12]', 'aesdec xmm3,oword [rbp + 12]'),
    ('AESDEC (MEM 3)', '660F38DE3544434241', 'aesdec xmm6,oword [rip + 1094861636]', 'aesdec xmm6,oword [rip + 1094861636]'),
    ('AESDECLAST', '660F38DFED', 'aesdeclast xmm5,xmm5', 'aesdeclast xmm5,xmm5'),
    ('AESDECLAST (MEM)', '660F38DF2E', 'aesdeclast xmm5,oword [rsi]', 'aesdeclast xmm5,oword [rsi]'),
    ('AESDECLAST (MEM 2)', '660F38DF6740', 'aesdeclast xmm4,oword [rdi + 64]', 'aesdeclast xmm4,oword [rdi + 64]'),
    ('AESDECLAST (MEM 3)', '660F38DF2511213141', 'aesdeclast xmm4,oword [rip + 1093738769]', 'aesdeclast xmm4,oword [rip + 1093738769]'),
    ('AESIMC', '660F38DBF9', 'aesimc xmm7,xmm1', 'aesimc xmm7,xmm1'),
    ('AESIMC (MEM)', '660F38DB13', 'aesimc xmm2,oword [rbx]', 'aesimc xmm2,oword [rbx]'),
    ('AESIMC (MEM 2)', '660F38DB5020', 'aesimc xmm2,oword [rax + 32]', 'aesimc xmm2,oword [rax + 32]'),
    ('AESIMC (MEM 3)', '660F38DB1D00000041', 'aesimc xmm3,oword [rip + 1090519040]', 'aesimc xmm3,oword [rip + 1090519040]'),
    ('AESKEYGENASSIST', '660F3ADFFE08', 'aeskeygenassist xmm7,xmm6,8', 'aeskeygenassist xmm7,xmm6,8'),
    ('AESKEYGENASSIST (MEM)', '660F3ADF1AFE', 'aeskeygenassist xmm3,oword [rdx],254', 'aeskeygenassist xmm3,oword [rdx],254'),
    ('AESKEYGENASSIST (MEM 2)', '660F3ADF998000000039', 'aeskeygenassist xmm3,oword [rcx + 128],57', 'aeskeygenassist xmm3,oword [rcx + 128],57'),
    ('AESKEYGENASSIST (MEM 3)', '660F3ADF2541414141C6', 'aeskeygenassist xmm4,oword [rip + 1094795585],198', 'aeskeygenassist xmm4,oword [rip + 1094795585],198'),
    ('PCLMULQDQ', '660F3A44D307', 'pclmulqdq xmm2,xmm3,7', 'pclmulqdq xmm2,xmm3,7'),
    ('PCLMULQDQ (MEM)', '660F3A441007', 'pclmulqdq xmm2,oword [rax],7', 'pclmulqdq xmm2,oword [rax],7'),
    ('PCLMULQDQ (MEM 2)', '660F3A4478119C', 'pclmulqdq xmm7,oword [rax + 17],156', 'pclmulqdq xmm7,oword [rax + 17],156'),
    ('PCLMULQDQ (MEM 3)', '660F3A443D41414141C6', 'pclmulqdq xmm7,oword [rip + 1094795585],198', 'pclmulqdq xmm7,oword [rip + 1094795585],198'),
    ('BLENDPD', '660F3A0DCA2F', 'blendpd xmm1,xmm2,47', 'blendpd xmm1,xmm2,47'),
    ('BLENDPS', '660F3A0C0C25414141415D', 'blendps xmm1,oword [0x41414141],93', 'blendps xmm1,oword [0x41414141],93'),
    ('BLENDVPS', '660F38140C2541414141', 'blendvps xmm1,oword [0x41414141]', 'blendvps xmm1,oword [0x41414141]'),
    ('BLENDVPS', '660F3814DC', 'blendvps xmm3,xmm4', 'blendvps xmm3,xmm4'),
    ('BLENDVPD', '660F38150C2541414141', 'blendvpd xmm1,oword [0x41414141]', 'blendvpd xmm1,oword [0x41414141]'),
    ('BLENDVPD', '660F3815DC', 'blendvpd xmm3,xmm4', 'blendvpd xmm3,xmm4'),
    ('PEXTRB', '660F3A14D011', 'pextrb eax,xmm2,17', 'pextrb eax,xmm2,17'),
    ('PEXTRB 2', '660F3A141011', 'pextrb dword [eax],xmm2,17', 'pextrb dword [rax],xmm2,17'),
    ('PEXTRB 3', '', 'pextrb dword [rax],xmm2,17', 'pextrb dword [rax],xmm2,17'),
    ('PEXTRD', '660F3A16EA11', 'pextrd edx,xmm5,17', 'pextrd edx,xmm5,17'),
    ('PEXTRD 2', '660F3A161011', 'pextrd dword [rax],xmm2,17', 'pextrd dword [rax],xmm2,17'),
    ('PEXTRD 3', '67660F3A162A11', 'pextrd dword [eax],xmm2,17', 'pextrd dword [eax],xmm2,17'),
    ('PEXTRQ', '66480F3A16D9FE', 'pextrq rcx,xmm3,254', 'pextrq rcx,xmm3,254'),
    ('PEXTRQ 2', '66480F3A16A14141414175', 'pextrq qword [rcx + 0x41414141],xmm4,117', 'pextrq qword [rcx + 0x41414141],xmm4,117'),
    ('PEXTRQ 3', '6766480F3A16A34141414175', 'pextrq qword [ebx+0x41414141],,xmm4,117', 'pextrq qword [ebx+0x41414141],,xmm4,117'),
    ('TEST', '67F70078563412', 'test dword [eax], 0x12345678', 'test dword [eax], 0x12345678'),
    ('TEST', 'F70078563412', 'test dword [rax], 0x12345678', 'test dword [eax], 0x12345678'),
]

amd64VexOpcodes = [
    #('PSRLW (VEX)', 'C5E9D1CB', '', ''),
    #('PSRLW (VEX) 1', 'C5F171D208', '', ''),
    #('PSRLW (VEX) 2', 'C5E9D10C2541414141', '', ''),
    #('PSRLW (VEX) 3', '67C5E9D108', 'vpsrlw xmm1,xmm2,[eax]', ''),
    ('ANDN', 'C4E260F2C1', 'andn eax,ebx,ecx', 'andn eax,ebx,ecx'),
    ('ANDN 2', 'C4E2E0F2C1', 'andn rax,rbx,rcx', 'andn rax,rbx,rcx'),
    ('BEXTR', 'C4E270F7D3', 'bextr edx,ebx,ecx', 'bextr edx,ebx,ecx'),
    ('BEXTR 2', 'C4E2F0F7D0', 'bextr rdx,rax,rcx', 'bextr rdx,rax,rcx'),
    ('BEXTR 3', 'C4E2F0F71541414100', 'bextr rdx,qword [rip + 4276545],rcx', 'bextr rdx,qword [rip + 4276545],rcx'),
    ('BLSI', 'c4e268f3d8', 'blsi edx,eax', 'blsi edx,eax'),
    ('BLSI 2', 'C4E268F31C2541414141', 'blsi edx,dword [0x41414141]', 'blsi edx,dword [0x41414141]'),
    ('BLSI 3', 'C4E2F0F31C2541414141', 'blsi rcx,qword [0x41414141]', 'blsi rcx,qword [0x41414141]'),
    ('BLSMSK', 'C4E2F0F3142541414141', 'blsmsk rcx,qword [0x41414141]', 'blsmsk rcx,qword [0x41414141]'),
    ('BLSMSK 2', 'C4E278F3D2', 'blsmsk eax,edx', 'blsmsk eax,edx'),
    ('BLSR', 'C4E278F3CB', 'blsr eax,ebx', 'blsr eax,ebx'),
    ('BLSR 2', '67C4E278F30B', 'blsr eax,dword [ebx]', 'blsr eax,dword [ebx]'),
    ('BLSR 3', 'C4E270F30C2541414141', 'blsr rcx, dword [0x41414141]', 'blsr rcx, dword [0x41414141]'),
    ('BLSR 4', 'C4E2F0F30B', 'blsr rcx,qword [rbx]', 'blsr rcx,qword [rbx]'),
    ('BLSR 5', 'C4E2E8F30C2541414141', 'blsr rdx,qword [0x41414141]', 'blsr rdx,qword [0x41414141]'),
    ('VMOVDQU', 'C5fe6fe3', 'vmovdqu ymm4,ymm3', 'vmovdqu ymm4,ymm3'),
    ('VLDDQU', 'C5FFF01C2541414141', 'vlddqu ymm3,0x41414141', 'vlddqu ymm3,0x41414141'),
    ('VLDDQU', 'C5FFF034D50400', 'vlddqu ymm6, [rdx*8+4]', 'vlddqu ymm6, [rdx*8+4]'),
    ('VLDDQU', 'C5FBF00CF504000000', 'vlddqu xmm1,[rsi*8+4]', 'vlddqu xmm1,[rsi*8+4]'),

    # w/ address size override
    ('VLDDQU', '67C5FBF00CF504000000', 'vlddqu xmm1,[esi*8+4]', 'vlddqu xmm1,[esi*8+4]'),
    ('VPSRLDQ', 'C5E9D3CB', 'vpsrlq xmm1,xmm2,xmm3', 'vpsrlq xmm1,xmm2,xmm3'),
    ('VPOR', 'C5EDEBCB', 'vpor ymm1,ymm2,ymm3', 'vpor ymm1,ymm2,ymm3'),
    ('VMOVSD', 'C5FB1008', 'vmovsd xmm1, oword [rax]', 'vmovsd xmm1,oword[rax]'),
    ('VMOVSD 2', 'C5EB10CB', 'vmovsd xmm1,xmm2,xmm3', 'vmovsd xmm1,xmm2,xmm3'),
    ('VMOVSD 3', '67C5FB1118', 'vmovsd oword [eax],xmm3', 'vmovsd oword [eax],xmm3'),
    ('VMOVSD 4', 'C5FB111C2541414141', 'vmovsd oword [0x41414141],xmm3', 'vmovsd oword [0x41414141],xmm3'),
    ('VSQRTPD', 'C5F951CA', 'vsqrtpd xmm1,xmm2', 'vsqrtpd xmm1,xmm2'),
    ('VSQRTPD 2', 'C5FD51CA', 'vsqrtpd ymm1,ymm2', 'vsqrtpd ymm1,ymm2'),
    ('VBLENDVPS (128)', 'C4E3694ACB40', 'vblendvps xmm1,xmm2,xmm3,xmm4', 'vblendvps xmm1,xmm2,xmm3,xmm4'),
    ('VBLENDVPS (MEM128)', 'C4E3694A0C254141414140', 'vblendvps xmm1,xmm2,oword [0x41414141],xmm4', ''),
    ('VBLENDVPS (256)', 'C4E36D4ACB40', 'vblendvps ymm1,ymm2,ymm3,ymm4', 'vblendvps ymm1,ymm2,ymm3,ymm4'),
    ('VBLENDVPS (MEM256)', 'C4E36D4A0C254141414140', 'vblendvps ymm1,ymm2,oword [0x41414141],ymm4', 'vblendvps ymm1,ymm2,oword [0x41414141],ymm4'),
    # ('VSQRTPD 3' ,'', 'vsqrtpd zmm1,zmm2', 'vsqrtpd zmm1,zmm2'),
]


class Amd64InstructionSet(unittest.TestCase):
    _arch = envi.getArchModule("amd64")

    def check_opreprs(self, opers):
        vw = vivisect.VivWorkspace()
        scanv = e_memcanvas.StringMemoryCanvas(vw)

        for name, bytez, reprOp, renderOp in opers:

            try:
                op = self._arch.archParseOpcode(bytez.decode('hex'), 0, 0x40)
            except envi.InvalidInstruction:
                self.fail("Failed to parse opcode bytes: %s (case: %s, expected: %s)" % (bytez, name, reprOp))

            try:
                self.assertEqual(repr(op), reprOp)
            except AssertionError:
                import pdb
                pdb.set_trace()
                self.fail("Failing match for case %s (bytes: %s) (Got: '%s', Expected: '%s')" % (name, bytez, repr(op), reprOp))

            scanv.clearCanvas()
            op.render(scanv)
            self.assertEqual(scanv.strval, renderOp)

    def test_envi_amd64_disasm_Specific_VEX_Instrs(self):
        self.check_opreprs(amd64VexOpcodes)

    def test_envi_amd64_disasm_Specific_SingleByte_Instrs(self):
        self.check_opreprs(amd64SingleByteOpcodes)

    def test_envi_amd64_disasm_Specific_MultiByte_Instrs(self):
        self.check_opreprs(amd64MultiByteOpcodes)

    def checkOpcode(self, hexbytez, va, oprepr, opcheck, opercheck, renderOp):

        op = self._arch.archParseOpcode(hexbytez.decode('hex'), 0, va)

        self.assertEqual( repr(op), oprepr )
        opvars = vars(op)
        for opk,opv in opcheck.items():
            #print "op: %s %s" % (opk,opv)
            self.assertEqual( (repr(op), opk, opvars.get(opk)), (oprepr, opk, opv) )

        for oidx in range(len(op.opers)):
            oper = op.opers[oidx]
            opervars = vars(oper)
            for opk,opv in opercheck[oidx].items():
                #print "oper: %s %s" % (opk,opv)
                self.assertEqual( (repr(op), opk, opervars.get(opk)), (oprepr, opk, opv) )

        vw = vivisect.VivWorkspace()
        scanv = e_memcanvas.StringMemoryCanvas(vw)
        op.render(scanv)
        #print "render:  %s" % repr(scanv.strval)
        self.assertEqual( scanv.strval, renderOp )

    ###############################################
    # only pick the operands special to 64-bit mode
    def test_envi_amd64_disasm_Reg_Operands(self):
        '''
        test an opcode encoded with an Reg operand
        _0      add al      04
        G       add         02
        C       mov         0f20
        D       mov         0f21
        P       punpcklbw   0f60
        S       mov         8c
        U       movmskps    0f50
        V       sqrtps      0f51
        _0      mov REX     41b*

        '''
        opbytez = '0032'
        oprepr = 'add byte [rdx],dh'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'add', 'opcode': 8193, 'size': 2}
        opercheck = [{'disp': 0, 'tsize': 1, '_is_deref': True, 'reg': 2}, {'tsize': 1, 'reg': 134742018}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '480032'
        oprepr = 'add byte [rdx],sil'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1572864, 'mnem': 'add', 'opcode': 8193, 'size': 3}
        opercheck = [{'disp': 0, 'tsize': 1, '_is_deref': True, 'reg': 2}, {'tsize': 1, 'reg': 524294}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '480132'
        oprepr = 'add qword [rdx],rsi'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1572864, 'mnem': 'add', 'opcode': 8193, 'size': 3}
        opercheck = [{'disp': 0, 'tsize': 8, '_is_deref': True, 'reg': 2}, {'tsize': 8, 'reg': 6}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '0440'
        oprepr = 'add al,64'
        opcheck = {'iflags': 131072, 'prefixes': 0, 'mnem': 'add', 'opcode': 8193, 'size': 2}
        opercheck = ( {'tsize': 4, 'reg': 524288}, {'tsize': 4, 'imm': 64} )
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '0218'
        oprepr = 'add bl,byte [rax]'
        opcheck = {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'add', 'opcode': 8193, 'size': 2}
        opercheck = ( {'tsize': 1, 'reg': 524291}, {'disp': 0, 'tsize': 1, '_is_deref': True, 'reg': 0} )
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '0f2018'
        oprepr = 'mov dword [rax],ctrl3'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'mov', 'opcode': 24577, 'size': 3}
        opercheck = ( {'disp': 0, 'tsize': 4, '_is_deref': True, 'reg': 0}, {'tsize': 4, 'reg': 59} )
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        for x in range(0xb0, 0xb8):
            bytez = '41%.2xAAAAAAAA' % x
            op = self._arch.archParseOpcode((bytez).decode('hex'),0,0x1000)
            self.assertEqual( (bytez, hex(op.opers[0].reg)), (bytez, hex( 0x80000 + (x-0xa8) )) )

        for x in range(0xb8, 0xc0):
            bytez = '41%.2xAAAAAAAA' % x
            op = self._arch.archParseOpcode((bytez).decode('hex'),0,0x1000)
            self.assertEqual( (bytez, hex(op.opers[0].reg)), (bytez, hex( 0x200000 + (x-0xb0) )) )




    def test_envi_amd64_disasm_Imm_Operands(self):
        '''
        test an opcode encoded with an Imm operand
        _0      rol         d000
        A       callf       9a
        '''
        opbytez = 'd000'
        oprepr = 'rol byte [rax],1'
        opcheck =  {'iflags': 131072, 'va': 16384, 'prefixes': 0, 'mnem': 'rol', 'opcode': 8201, 'size': 2}
        opercheck = ( {'disp': 0, 'tsize': 1, '_is_deref': True, 'reg': 0}, {'tsize': 4, 'imm': 1} )
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )
       
        # this is failing legitimately... we decode this opcode wrong
        opbytez = '9aaa11aabbcc33'
        oprepr = 'callf 0x33cc:0xbbaa11aa'
        opcheck =  {'iflags': 131076, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'callf', 'opcode': 4099, 'size': 7}
        opercheck = [{'tsize': 6, 'imm': 56954414829994}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [3]: generateTestInfo('413ac4')
        opbytez = '413ac4'
        oprepr = 'cmp al,r12l'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1114112, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 1, 'reg': 524288}, {'tsize': 1, 'reg': 524300}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [4]: generateTestInfo('453ac4')
        opbytez = '453ac4'
        oprepr = 'cmp r8l,r12l'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1376256, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 1, 'reg': 524296}, {'tsize': 1, 'reg': 524300}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [5]: generateTestInfo('473ac4')
        opbytez = '473ac4'
        oprepr = 'cmp r8l,r12l'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1507328, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 1, 'reg': 524296}, {'tsize': 1, 'reg': 524300}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [3]: generateTestInfo('3ac4')
        opbytez = '3ac4'
        oprepr = 'cmp al,ah'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'cmp', 'opcode': 20482, 'size': 2}
        opercheck = [{'tsize': 1, 'reg': 524288}, {'tsize': 1, 'reg': 134742016}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [4]: generateTestInfo('403ac4')
        opbytez = '403ac4'
        oprepr = 'cmp al,spl'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1048576, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 1, 'reg': 524288}, {'tsize': 1, 'reg': 524292}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [5]: generateTestInfo('663ac4')
        opbytez = '663ac4'
        oprepr = 'cmp al,ah'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 64, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 1, 'reg': 524288}, {'tsize': 1, 'reg': 134742016}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [6]: generateTestInfo('673ac4')
        opbytez = '673ac4'
        oprepr = 'addr: cmp al,ah'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 128, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 1, 'reg': 524288}, {'tsize': 1, 'reg': 134742016}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [7]: generateTestInfo('663ac4')
        opbytez = '663ac4'
        oprepr = 'cmp al,ah'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 64, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 1, 'reg': 524288}, {'tsize': 1, 'reg': 134742016}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [9]: generateTestInfo('663bc4')
        opbytez = '663bc4'
        oprepr = 'cmp ax,sp'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 64, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 2, 'reg': 1048576}, {'tsize': 2, 'reg': 1048580}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [10]: generateTestInfo('3bc4')
        opbytez = '3bc4'
        oprepr = 'cmp eax,esp'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'cmp', 'opcode': 20482, 'size': 2}
        opercheck = [{'tsize': 4, 'reg': 2097152}, {'tsize': 4, 'reg': 2097156}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [11]: generateTestInfo('403bc4')
        opbytez = '403bc4'
        oprepr = 'cmp eax,esp'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1048576, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 4, 'reg': 2097152}, {'tsize': 4, 'reg': 2097156}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [12]: generateTestInfo('413bc4')
        opbytez = '413bc4'
        oprepr = 'cmp eax,r12d'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1114112, 'mnem': 'cmp', 'opcode': 20482, 'size': 3}
        opercheck = [{'tsize': 4, 'reg': 2097152}, {'tsize': 4, 'reg': 2097164}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        #In [13]: generateTestInfo('66413bc4')
        opbytez = '66413bc4'
        oprepr = 'cmp ax,r12w'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1114176, 'mnem': 'cmp', 'opcode': 20482, 'size': 4}
        opercheck = [{'tsize': 2, 'reg': 1048576}, {'tsize': 2, 'reg': 1048588}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )



    def test_envi_amd64_disasm_PcRel_Operands(self):
        '''
        test an opcode encoded with an PcRelative operand
        '''
        pass

    def test_envi_amd64_disasm_RegMem_Operands(self):
        '''
        test an opcode encoded with an RegMem operand
        X       outsb       6e
        Y       insd        6d
        '''
        opbytez = '6e'
        oprepr = 'outsb dx,byte [rsi]'
        opcheck =  {'iflags': 131074, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'outsb', 'opcode': 57347, 'size': 1}
        opercheck = [{'tsize': 4, 'reg': 1048578}, {'disp': 0, 'tsize': 1, '_is_deref': True, 'reg': 6}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '6d'
        oprepr = 'insd dword [rsi],dx'
        opcheck =  {'iflags': 131074, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'insd', 'opcode': 57346, 'size': 1}
        opercheck = [{'disp': 0, 'tsize': 4, '_is_deref': True, 'reg': 6}, {'tsize': 4, 'reg': 1048578}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

    def test_envi_amd64_disasm_ImmMem_Operands(self):
        '''
        test an opcode encoded with an ImmMem operand
        O       mov         a1
        '''
        opbytez = 'a1a2345678aabbccdd'
        oprepr = 'mov eax,dword [0xddccbbaa785634a2]'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'mov', 'opcode': 24577, 'size': 9}
        opercheck = [{'tsize': 4, 'reg': 2097152}, {'tsize': 4, '_is_deref': True, 'imm': 15982355518468797602L}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

    def test_envi_amd64_disasm_SIB_Operands(self):
        '''
        exercize the entire SIB operand space
        A       jmp         fa
        E       lar         0f02
        Q       cvttps2pi   0f2c
        W       cvttps2pi   0f2c
        with REX:
                mov qword [rsp + r12 * 8 + 32],rdi  4a897ce420
        '''
        opbytez = 'eaa123456789ab'          # this wants more bytes, why?
        oprepr = 'jmp 0xab89:0x674523a1'       # this repr's wrong.  it should be ab89:674523a1
        opcheck =  {'iflags': 131081, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'jmp', 'opcode': 4097, 'size': 7}
        opercheck = [{'tsize': 6, 'imm': 188606631453601}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '0f02aabbccddee'
        oprepr = 'lar ebp,word [rdx - 287454021]'
        opcheck =  {'iflags': 131074, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'lar', 'opcode': 57344, 'size': 7}
        opercheck = [{'tsize': 4, 'reg': 2097157}, {'disp': -287454021, 'tsize': 2, '_is_deref': True, 'reg': 2}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '0f2caabbccddeeff'
        oprepr = 'cvttps2pi mm5,oword [rdx - 287454021]'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'cvttps2pi', 'opcode': 61440, 'size': 7}
        opercheck = [{'tsize': 8, 'reg': 21}, {'disp': -287454021, 'tsize': 16, '_is_deref': True, 'reg': 2}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )


        opbytez = '3b80ABCDEF12'
        oprepr = 'cmp eax,dword [rax + 317705643]'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 0, 'mnem': 'cmp', 'opcode': 20482, 'size': 6}
        opercheck = [{'tsize': 4, 'reg': 2097152}, {'disp': 317705643, 'tsize': 4, '_is_deref': True, 'reg': 0}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )

        opbytez = '4a897ce420'
        oprepr = 'mov qword [rsp + r12 * 8 + 32],rdi'
        opcheck =  {'iflags': 131072, 'va': 16384, 'repr': None, 'prefixes': 1703936, 'mnem': 'mov', 'opcode': 24577, 'size': 5}
        opercheck = [{'disp': 32, 'index': 12, 'tsize': 8, 'scale': 8, 'imm': None, '_is_deref': True, 'reg': 4}, {'tsize': 8, 'reg': 7}]
        self.checkOpcode( opbytez, 0x4000, oprepr, opcheck, opercheck, oprepr )


def generateTestInfo(ophexbytez='6e'):
    a64 = e_amd64.Amd64Module()
    opbytez = ophexbytez
    op = a64.archParseOpcode(opbytez.decode('hex'), 0, 0x4000)
    print "opbytez = '%s'\noprepr = '%s'"%(opbytez,repr(op))
    opvars=vars(op)
    opers = opvars.pop('opers')
    print "opcheck = ",repr(opvars)

    opersvars = []
    for x in range(len(opers)):
        opervars = vars(opers[x])
        opervars.pop('_dis_regctx')
        opersvars.append(opervars)

    print "opercheck = %s" % (repr(opersvars))

