using ErnestWorld;
using ErnestWorld.Services;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;

var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");
builder.RootComponents.Add<HeadOutlet>("head::after");

builder.Services.AddScoped(_ => new HttpClient { BaseAddress = new Uri(builder.HostEnvironment.BaseAddress) });

// Les services du site (dans Blazor WebAssembly, « Scoped » = un seul exemplaire par onglet)
builder.Services.AddScoped<ToastService>();
builder.Services.AddScoped<BrowserService>();
builder.Services.AddScoped<GameState>();
builder.Services.AddScoped<BlogService>();
builder.Services.AddScoped<WorldService>();
builder.Services.AddScoped<NewsletterService>();

await builder.Build().RunAsync();
