BES 各个模块

**应用管理** ： 部署应用、部署公共类库、
**服务管理** ： Web容器管理（线程、线程池管理）、安全服务（提供一些非安全方法拦截、记录日志等）
**资源管理**： JDBC、JMS等
**监控管理**： 实时监控，监控快照等
**CLI 模块**： 提供命令行来管理 AppServer



类加载流程


### 1. 部署触发

首先创建一个 `StandardContext` 容器来表示该应用，随后进入部署流程。

### 2. 创建 WebappClassLoader

- 在 `Context` 初始化阶段，当前应用创建一个独立的 `WebappClassLoader` 实例。
- 该加载器的**父加载器**通常是 `SharedClassLoader`（默认与 `CommonClassLoader` 为同一实例），确保容器公共类（如 `servlet-api.jar`）由父加载器加载，实现共享。
- `WebappClassLoader` 的类路径被设置为：
    - `WEB-INF/classes`（优先）
    - `WEB-INF/lib/*.jar`（按文件名顺序）
- 该加载器被绑定到 `Context` 的 `loader` 属性，后续该应用内的所有类加载都通过它完成。

### 3. 加载应用的配置类
解析应用的部署描述符（`web.xml`）和注解（通过 `javax.servlet.annotation`），并使用 `WebappClassLoader` 加载以下组件类：
- **`ServletContainerInitializer`**（通过 `META-INF/services` 机制）
- **监听器**（`ServletContextListener` 等）
- **过滤器**（`Filter`）
- **Servlet**（`Servlet`）
- 其他配置中引用的类（如 `<load-on-startup>` 标记的 Servlet

### 4. 初始化与启动

- 加载完成后，会实例化并调用这些组件的初始化方法（如 `contextInitialized`）。
- 对于 `<load-on-startup>` 的 Servlet，会立即调用其 `init()` 方法；其他 Servlet 则延迟到首次请求时加载。

### 5. 热部署时的类加载器替换

当应用被重新部署（如替换 WAR 文件）时，会：
- 创建一个 **新的** `WebappClassLoader` 实例。
- 使用新的加载器加载新版应用的配置类。
- 完成初始化后，逐步停止旧应用，并销毁旧的 `WebappClassLoader`（使其失去引用，最终被 GC 回收），实现旧类卸载和新类加载。

我总结一下
他读了一本书《控制论和科学方法论》（这肯定是一本经典好书），然后呢想噶韭菜了，那怎么办呢？和AI结合起来呗。

首先呢，跑去AI社区搜一下相似的关键字，Harness Engineering。我总结了一下他列的两篇文章，他自己也总结了。文章主要说的是让ai来写代码，比人类手写效率高多少之类的。然后就是怎么给AI喂上下文最好。和他的文章不能说是毫不相干，至少也是风马牛不相及。

他也不确定这是不是就是控制论。老外肯定也没读过吗那本书。但是他相信 “Harness Engineering 就是控制论” 他的原话。

因为受限于现在的大模型上下文长度有限。除了claude 4.6是1M，其他的模型基本都在 64k-256K。所以必须要控制输入的信息精确度。有些工程师，总结了一下。然后他就套到了他读的这本书上面。

最后呢，《控制论和科学方法论》这本书说的是用控制论的角度去理解科学观，从一个角度去带大家去认识科学方法论。
书是好书，AI也是真好用。
但是实际上真正落地需要的是各种
但是这种文章坏就坏在非要拉AI来掺一脚。好像就是说AI能发展起来就得益于这些指导思想一样，你想去