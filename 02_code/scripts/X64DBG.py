from x64dbg_automate import X64DbgClient

client = X64DbgClient(x64dbg_path=r"E:\JerichoSoft\x64dbg\release\x64\x64dbg.exe")
print("PID:", client.get_current_process_pid())
print("RIP:", hex(client.get_register("rip")))
client.detach()